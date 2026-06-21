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

    Pass KHÔNG tự emit `run_error` — để caller quyết."""
    __slots__ = ("ok", "results", "out_keys", "labels", "node_keys", "error")

    def __init__(self, ok, results, out_keys, labels, node_keys, error=None):
        self.ok = ok
        self.results = results
        self.out_keys = out_keys
        self.labels = labels
        self.node_keys = node_keys  # node_id -> nk
        self.error = error


async def _execute_pass(order: list[str], nodes_by_id: dict, incoming: dict,
                        emit: EventCallback, *, force_ids: frozenset) -> PassResult:
    """Chạy 1 lượt topo theo `order`, emit event từng node.

    Trả `PassResult`. Node lỗi → emit `node_error`, trả `ok=False` (KHÔNG emit
    run_error — caller quyết)."""
    results: dict[tuple[str, str], Any] = {}
    out_keys: dict[tuple[str, str], str] = {}
    # nhãn (mô tả ảnh) của từng output ảnh → đi theo ảnh xuống node con
    labels: dict[tuple[str, str], str] = {}
    node_keys: dict[str, str] = {}

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
                       force_ids: frozenset = frozenset()) -> None:
    """Thực thi workflow theo thứ tự topo, bắn event cho từng node.

    Cache địa chỉ-nội-dung: node có cache (key trùng) & không bị ép → dùng lại
    output, KHÔNG thực thi. `target` → chỉ chạy node đó + tổ tiên. `force_ids` →
    luôn chạy thật (kể cả có cache).

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

    res = await _execute_pass(order, nodes_by_id, incoming, emit, force_ids=force_ids)
    if not res.ok:
        await emit(RunEvent(type="run_error", message=res.error))
        return

    await emit(RunEvent(type="run_finished"))
