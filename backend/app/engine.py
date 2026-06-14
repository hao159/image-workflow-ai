import asyncio
import base64
import hashlib
import io
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from PIL import Image

from . import cache
from .engine_cache_key import (code_hash, key_params_excluding_labels,
                               label_out_key, label_params, node_key,
                               prune_to_ancestors)
from .models import RunEvent, Workflow
from .nodes import get_node_class
from .nodes.prompt_merge import merge_prompt
from .providers import resolve_model_config

GENERATIVE_TYPES = {"generate_image", "edit_image"}
MAX_FEEDBACKS = 3  # số chỉnh sửa gần nhất tích lũy vào prompt (tránh prompt phình)

EventCallback = Callable[[RunEvent], Awaitable[None]]

PREVIEW_MAX = 512


def _make_preview(data: bytes) -> str:
    img = Image.open(io.BytesIO(data))
    img.thumbnail((PREVIEW_MAX, PREVIEW_MAX))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _topo_order(workflow: Workflow) -> list[str]:
    indegree: dict[str, int] = {n.id: 0 for n in workflow.nodes}
    children: dict[str, list[str]] = defaultdict(list)
    for e in workflow.edges:
        if e.source not in indegree or e.target not in indegree:
            raise ValueError(f"Cạnh nối tới node không tồn tại: {e.source} -> {e.target}")
        indegree[e.target] += 1
        children[e.source].append(e.target)

    queue = deque(sorted(nid for nid, d in indegree.items() if d == 0))
    order: list[str] = []
    while queue:
        nid = queue.popleft()
        order.append(nid)
        for child in children[nid]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(order) != len(workflow.nodes):
        raise ValueError("Workflow có vòng lặp (cycle) — không thể thực thi.")
    return order


def _meta(outputs: dict[str, Any]) -> dict[str, Any]:
    """Metadata gửi về UI cho mỗi output (image→size, text→value). Dùng chung hit/miss."""
    out_meta: dict[str, Any] = {}
    for handle, value in outputs.items():
        if isinstance(value, bytes):
            # sha = tên blob cache (content-addressed) → frontend dựng URL
            # /api/cache-image/{sha} để xem/tải ảnh GỐC full-res (preview chỉ là
            # thumbnail JPEG). Khớp sha blob vì cache.save() ghi blob trước khi emit.
            out_meta[handle] = {
                "dtype": "image",
                "size": len(value),
                "sha": hashlib.sha256(value).hexdigest(),
            }
        else:
            out_meta[handle] = {"dtype": "text", "value": str(value)}
    return out_meta


async def _make_preview_safe(outputs: dict[str, Any], node_id: str):
    """Preview từ output ảnh đầu tiên decode được. Preview hỏng không giết run."""
    for value in outputs.values():
        if isinstance(value, bytes):
            try:
                return await asyncio.to_thread(_make_preview, value)
            except Exception as e:  # noqa: BLE001
                print(f"[engine] không tạo được preview node {node_id}: {e}")
    return None


class PassResult:
    """Kết quả 1 lượt chạy topo (1 pass). `ok=False` → node lỗi giữa chừng.

    Giữ `results`/`out_keys`/`labels`/`node_keys` để harness loop (Phase 2) lấy ảnh
    sản phẩm + truy node_key. Pass KHÔNG tự emit `run_error` — để caller quyết
    (chạy thường = run_error; harness = recovery giữ best)."""
    __slots__ = ("ok", "results", "out_keys", "labels", "node_keys", "error")

    def __init__(self, ok, results, out_keys, labels, node_keys, error=None):
        self.ok = ok
        self.results = results
        self.out_keys = out_keys
        self.labels = labels
        self.node_keys = node_keys  # node_id -> nk
        self.error = error


async def _execute_pass(order: list[str], nodes_by_id: dict, incoming: dict,
                        emit: EventCallback, *, force_ids: frozenset,
                        params_override: dict | None = None) -> PassResult:
    """Chạy 1 lượt topo theo `order`, emit event từng node. STATE TƯƠI mỗi lần gọi
    (results/out_keys/labels mới) → harness gọi lại nhiều lần không vấy bẩn.

    `params_override`: {node_id: {param: value}} ghi đè params (harness inject
    feedback vào node sinh). Áp TRƯỚC khi tính node_key → param đổi → key lan xuống.

    Trả `PassResult`. Node lỗi → emit `node_error`, trả `ok=False` (KHÔNG emit
    run_error — caller quyết)."""
    results: dict[tuple[str, str], Any] = {}
    out_keys: dict[tuple[str, str], str] = {}
    # nhãn (mô tả ảnh) của từng output ảnh → đi theo ảnh xuống node con
    labels: dict[tuple[str, str], str] = {}
    node_keys: dict[str, str] = {}
    overrides = params_override or {}

    for node_id in order:
        node_def = nodes_by_id[node_id]
        try:
            cls = get_node_class(node_def.type)
        except ValueError as e:
            await emit(RunEvent(type="node_error", node_id=node_id, message=str(e)))
            return PassResult(False, results, out_keys, labels, node_keys, str(e))

        # Gom value + out_key + nhãn SONG SONG theo từng dây (cùng thứ tự cạnh)
        gathered: dict[str, list[Any]] = defaultdict(list)
        in_keys: dict[str, list[str]] = defaultdict(list)
        gathered_labels: dict[str, list[str]] = defaultdict(list)
        for target_handle, src_id, src_handle in incoming[node_id]:
            src = (src_id, src_handle)
            if src in results:
                gathered[target_handle].append(results[src])
                in_keys[target_handle].append(out_keys.get(src, ""))
                gathered_labels[target_handle].append(labels.get(src, ""))
        # cổng multiple nhận list mọi dây nối vào; cổng thường lấy giá trị cuối
        multi_ports = {p.name for p in cls.inputs if p.multiple}
        inputs: dict[str, Any] = {
            handle: values if handle in multi_ports else values[-1]
            for handle, values in gathered.items()
        }

        params = cls.resolve_params(node_def.params)
        if node_id in overrides:  # harness: inject feedback vào params node sinh
            params = {**params, **overrides[node_id]}
        # node_key BỎ param nhãn → đổi mô tả KHÔNG đổi key → không sinh lại ảnh AI.
        label_names = label_params(cls)
        nk = node_key(node_def.type, key_params_excluding_labels(params, label_names),
                      dict(in_keys), code_hash(cls))
        node_keys[node_id] = nk

        # Nhãn OUTPUT ảnh: param riêng (load/generate) ưu tiên; không có thì kế thừa
        # từ cổng input (node Biến đổi); còn lại rỗng (vd edit_image → ảnh ghép).
        own_label = next((str(params[n]) for n in label_names
                          if (params.get(n) or "").strip()), "")
        passthrough = cls.label_passthrough_from
        if own_label:
            out_label = own_label
        elif passthrough and gathered_labels.get(passthrough):
            out_label = gathered_labels[passthrough][-1]
        else:
            out_label = ""
        image_out_handles = {p.name for p in cls.outputs if p.dtype == "image"}

        def record_outputs(out_dict):
            """Ghi results + out_key + labels (dùng chung nhánh cache-hit & chạy thật).
            Output ảnh: out_key nối hash nhãn (downstream chạy lại khi nhãn đổi) +
            ghi labels map; output text: out_key thường."""
            for handle, value in out_dict.items():
                results[(node_id, handle)] = value
                base = f"{nk}:{handle}"
                if handle in image_out_handles:
                    out_keys[(node_id, handle)] = label_out_key(base, out_label)
                    labels[(node_id, handle)] = out_label
                else:
                    out_keys[(node_id, handle)] = base

        await emit(RunEvent(type="node_started", node_id=node_id))

        cached = None if node_id in force_ids else cache.load(nk)
        if cached is not None:
            record_outputs(cached.outputs)
            await emit(RunEvent(type="node_finished", node_id=node_id,
                                preview=cached.preview, outputs=_meta(cached.outputs),
                                cached=True))
            continue

        instance = cls()
        instance.input_labels = dict(gathered_labels)
        try:
            outputs = await asyncio.to_thread(instance.run, inputs, params)
        except Exception as e:  # noqa: BLE001 — mọi lỗi node đều báo về UI
            msg = f"{cls.title}: {e}"
            await emit(RunEvent(type="node_error", node_id=node_id, message=msg))
            return PassResult(False, results, out_keys, labels, node_keys, msg)

        record_outputs(outputs)
        preview = await _make_preview_safe(outputs, node_id)
        cache.save(nk, outputs, preview)
        await emit(RunEvent(type="node_finished", node_id=node_id,
                            preview=preview, outputs=_meta(outputs), cached=False))

    return PassResult(True, results, out_keys, labels, node_keys)


async def run_workflow(workflow: Workflow, emit: EventCallback, *,
                       target: str | None = None,
                       force_ids: frozenset = frozenset(),
                       harness: Any = None) -> None:
    """Thực thi workflow theo thứ tự topo, bắn event cho từng node.

    Cache địa chỉ-nội-dung: node có cache (key trùng) & không bị ép → dùng lại
    output, KHÔNG thực thi. `target` → chỉ chạy node đó + tổ tiên. `force_ids` →
    luôn chạy thật (kể cả có cache).

    `harness`: bật chế độ critic-refine loop (Phase 2). None/disabled → chạy 1 pass
    như cũ (backward compat).

    Bất biến quan trọng: ép chạy lại (force) KHÔNG đổi node_key của node đó → node
    con (key không đổi) vẫn cache-HIT giá trị cũ, không thấy output vừa sinh. Muốn
    downstream thấy output mới phải: (a) dùng `target` để prune bỏ downstream, hoặc
    (b) đổi param/input khiến key lan xuống. Nút ▶ trên node gửi target=node +
    force=[node] nên downstream luôn bị prune — an toàn."""
    await emit(RunEvent(type="run_started"))
    try:
        order = _topo_order(workflow)
    except ValueError as e:
        await emit(RunEvent(type="run_error", message=str(e)))
        return

    if target is not None:
        order = prune_to_ancestors(order, target, workflow.edges)

    nodes_by_id = {n.id: n for n in workflow.nodes}
    # target_id -> [(target_handle, source_id, source_handle)]
    incoming: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for e in workflow.edges:
        incoming[e.target].append((e.targetHandle or "", e.source, e.sourceHandle or ""))

    if harness is not None and getattr(harness, "enabled", False):
        await _run_harness(order, nodes_by_id, incoming, emit,
                           force_ids=force_ids, harness=harness)
        return

    res = await _execute_pass(order, nodes_by_id, incoming, emit, force_ids=force_ids)
    if not res.ok:
        await emit(RunEvent(type="run_error", message=res.error))
        return

    await emit(RunEvent(type="run_finished"))


# ============================ Harness critic-refine loop ============================

def _image_in_handles(cls) -> set[str]:
    return {p.name for p in cls.inputs if p.dtype == "image"}


def _nearest_generative(node_id: str, nodes_by_id: dict, incoming: dict) -> str | None:
    """Truy ngược từ node sản phẩm qua các cạnh ảnh tới node Tạo/Sửa ảnh gần nhất."""
    seen: set[str] = set()
    stack = [node_id]
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        if nodes_by_id[nid].type in GENERATIVE_TYPES:
            return nid
        img_in = _image_in_handles(get_node_class(nodes_by_id[nid].type))
        for th, sid, _sh in incoming[nid]:
            if th in img_in:
                stack.append(sid)
    return None


def _locate_product(order: list[str], nodes_by_id: dict, incoming: dict):
    """Tìm (sink_ids, product=(node_id,handle), gen_id) cho harness.

    sink = node có cổng ảnh VÀO nhưng KHÔNG có cổng ảnh RA (vd save_image) → chạy
    1 lần trên best sau loop. product = ảnh vào sink (hoặc ảnh terminal nếu không có
    sink). gen = node Tạo/Sửa ảnh gần nhất phía trên product. Nhập nhằng → ValueError."""
    sink_ids: set[str] = set()
    for nid in order:
        cls = get_node_class(nodes_by_id[nid].type)
        has_img_in = any(p.dtype == "image" for p in cls.inputs)
        has_img_out = any(p.dtype == "image" for p in cls.outputs)
        if has_img_in and not has_img_out:
            sink_ids.add(nid)
    if len(sink_ids) > 1:
        raise ValueError("Harness chưa hỗ trợ nhiều node đầu ra ảnh — chạy 1 nhánh.")

    if sink_ids:
        sink = next(iter(sink_ids))
        img_in = _image_in_handles(get_node_class(nodes_by_id[sink].type))
        product = None
        for th, sid, sh in incoming[sink]:
            if th in img_in:
                product = (sid, sh)
        if product is None:
            raise ValueError("Node đầu ra (Lưu ảnh) chưa nối ảnh vào.")
    else:
        consumed = {(sid, sh) for nid in order for _th, sid, sh in incoming[nid]}
        terminals = [(nid, p.name) for nid in order
                     for p in get_node_class(nodes_by_id[nid].type).outputs
                     if p.dtype == "image" and (nid, p.name) not in consumed]
        if not terminals:
            raise ValueError("Harness cần ít nhất 1 node tạo/sửa ảnh có đầu ra ảnh.")
        if len(terminals) > 1:
            raise ValueError("Harness chưa hỗ trợ nhiều ảnh đầu ra — chạy 1 nhánh.")
        product = terminals[0]

    gen_id = _nearest_generative(product[0], nodes_by_id, incoming)
    if gen_id is None:
        raise ValueError("Harness cần ít nhất 1 node Tạo/Sửa ảnh trên nhánh sản phẩm.")
    return sink_ids, product, gen_id


def _effective_prompt(gen_id: str, nodes_by_id: dict, incoming: dict, results: dict) -> str:
    """Prompt hiệu dụng node sinh = merge(prompt cổng nối, param prompt) — y node làm."""
    cls = get_node_class(nodes_by_id[gen_id].type)
    params = cls.resolve_params(nodes_by_id[gen_id].params)
    connected = None
    for th, sid, sh in incoming[gen_id]:
        if th == "prompt" and (sid, sh) in results:
            connected = results[(sid, sh)]
    return merge_prompt(connected, params.get("prompt"))


def _prompt_with_feedback(orig_param: str, feedbacks: list[str]) -> str:
    """Ghép param prompt gốc + các feedback tích lũy (cap MAX_FEEDBACKS gần nhất)."""
    base = (orig_param or "").strip()
    recent = [f.strip() for f in feedbacks[-MAX_FEEDBACKS:] if f and f.strip()]
    if not recent:
        return base
    fb = "Phản hồi chỉnh sửa (áp dụng tất cả): " + " | ".join(recent)
    return f"{base}\n\n{fb}" if base else fb


async def _run_sinks_once(sink_ids: set, best_image: bytes, nodes_by_id: dict,
                          incoming: dict, last_results: dict, emit: EventCallback) -> bool:
    """Chạy node đầu ra (save) MỘT LẦN trên ảnh best → tránh ghi N file + best≠last.
    Trả False nếu sink lỗi (caller emit run_error).

    Bất biến: sink phải CHỈ tiêu thụ ảnh (vd save_image). Cổng ảnh được đè bằng best;
    cổng text (nếu có ở sink tương lai) lấy từ `last_results` của pass cuối → có thể
    lệch iteration so với best. Sink hiện tại không có cổng text nên an toàn."""
    for sink_id in sorted(sink_ids):
        cls = get_node_class(nodes_by_id[sink_id].type)
        params = cls.resolve_params(nodes_by_id[sink_id].params)
        inputs: dict[str, Any] = {}
        for th, sid, sh in incoming[sink_id]:
            if (sid, sh) in last_results:
                inputs[th] = last_results[(sid, sh)]
        for h in _image_in_handles(cls):  # đè ảnh vào = best
            inputs[h] = best_image
        await emit(RunEvent(type="node_started", node_id=sink_id))
        try:
            outputs = await asyncio.to_thread(cls().run, inputs, params)
        except Exception as e:  # noqa: BLE001
            await emit(RunEvent(type="node_error", node_id=sink_id,
                                message=f"{cls.title}: {e}"))
            return False
        preview = await _make_preview_safe(outputs, sink_id)
        await emit(RunEvent(type="node_finished", node_id=sink_id, preview=preview,
                            outputs=_meta(outputs), cached=False))
    return True


async def _run_harness(order: list[str], nodes_by_id: dict, incoming: dict,
                       emit: EventCallback, *, force_ids: frozenset, harness) -> None:
    """Vòng critic-refine có limit: chạy producers → critic chấm ảnh sản phẩm vs goal
    → chưa đạt thì append feedback vào prompt node sinh, re-run → lặp. Hết/đạt → chạy
    sink 1 lần trên best + emit report. Opt-in (run_workflow đã kiểm enabled)."""
    try:
        sink_ids, product, gen_id = _locate_product(order, nodes_by_id, incoming)
    except ValueError as e:
        await emit(RunEvent(type="run_error", message=str(e)))
        return

    # Critic provider: chỉ định riêng > provider node sinh. Kiểm vision TRƯỚC khi sinh.
    critic_sel = harness.critic_provider or (
        get_node_class(nodes_by_id[gen_id].type).resolve_params(
            nodes_by_id[gen_id].params).get("provider") or "")
    try:
        critic, critic_model = resolve_model_config(critic_sel)
    except Exception as e:  # noqa: BLE001
        await emit(RunEvent(type="run_error", message=f"Harness critic: {e}"))
        return
    if not type(critic).supports_critique():
        await emit(RunEvent(type="run_error", message=(
            "Harness cần critic có vision (Gemini) để chấm ảnh. Cấu hình "
            "critic_provider là một model Gemini trong ⚙ Cài đặt.")))
        return

    orig_prompt = get_node_class(nodes_by_id[gen_id].type).resolve_params(
        nodes_by_id[gen_id].params).get("prompt", "")
    producers = [nid for nid in order if nid not in sink_ids]
    max_iter = max(1, int(harness.max_iterations or 1))
    best = None          # {"score","image","iteration"}
    feedbacks: list[str] = []
    goal = None
    history: list[dict] = []
    last_results: dict = {}

    for it in range(max_iter):
        overrides = {}
        if feedbacks:
            overrides = {gen_id: {"prompt": _prompt_with_feedback(orig_prompt, feedbacks)}}
        res = await _execute_pass(producers, nodes_by_id, incoming, emit,
                                  force_ids=force_ids, params_override=overrides)
        if not res.ok:  # node lỗi giữa loop — giữ best nếu có (recovery)
            if best is not None:
                ok = await _run_sinks_once(sink_ids, best["image"], nodes_by_id,
                                           incoming, last_results, emit)
                await emit(RunEvent(type="harness_report", report={
                    "best_iteration": best["iteration"], "best_score": best["score"],
                    "history": history, "stopped_early": res.error}))
                await emit(RunEvent(type="run_finished" if ok else "run_error",
                                    message=None if ok else res.error))
            else:
                await emit(RunEvent(type="run_error", message=res.error))
            return
        last_results = res.results
        if goal is None:
            goal = _effective_prompt(gen_id, nodes_by_id, incoming, res.results)
        product_img = res.results.get(product)
        if not isinstance(product_img, (bytes, bytearray)):
            await emit(RunEvent(type="run_error",
                               message="Harness: không lấy được ảnh sản phẩm cuối."))
            return
        try:
            verdict = await asyncio.to_thread(
                critic.critique_image, bytes(product_img), goal, harness.criteria,
                model=critic_model)
        except Exception as e:  # noqa: BLE001
            await emit(RunEvent(type="run_error", message=f"Harness critic lỗi: {e}"))
            return
        score = float(verdict.get("score") or 0.0)
        passed = bool(verdict.get("passed")) or score >= float(harness.pass_score)
        feedback = str(verdict.get("feedback") or "")
        await emit(RunEvent(type="harness_iteration", iteration=it, score=score,
                            passed=passed, message=feedback))
        history.append({"iteration": it, "score": score, "passed": passed})
        if best is None or score > best["score"]:
            best = {"score": score, "image": bytes(product_img), "iteration": it}
        if passed:
            break
        feedbacks.append(feedback)

    ok = await _run_sinks_once(sink_ids, best["image"], nodes_by_id,
                               incoming, last_results, emit)
    if not ok:
        await emit(RunEvent(type="run_error", message="Harness: node đầu ra lỗi."))
        return
    await emit(RunEvent(type="harness_report", report={
        "best_iteration": best["iteration"], "best_score": best["score"],
        "history": history}))
    await emit(RunEvent(type="run_finished"))
