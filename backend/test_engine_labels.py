"""Test engine: nhãn (mô tả ảnh) đi theo ảnh + cache đúng.

Bất biến cần khóa:
  - Đánh số "Ảnh N" theo đúng thứ tự ảnh (gốc = Ảnh 1, rồi cổng images).
  - Đổi mô tả ở node nguồn → KHÔNG gọi lại provider.generate (cache-hit) nhưng
    node "Sửa ảnh" phía dưới chạy lại với prompt mới.
  - Nhãn sống sót qua node "Biến đổi" (resize) — passthrough.
  - Workflow không nhãn → prompt edit y như cũ (backward compat).

Test thuần Python — KHÔNG cần server/token. Provider thay bằng stub qua monkeypatch
resolve_model_config trên TỪNG module node (app.nodes.generate / .edit), KHÔNG patch
app.providers (node bind tên qua `from ..providers import resolve_model_config`).

Chạy: backend\\.venv\\Scripts\\python.exe test_engine_labels.py
"""
import asyncio
import tempfile
from pathlib import Path

from app import cache
from app.engine import run_workflow
from app.engine_cache_key import (key_params_excluding_labels, label_out_key,
                                   label_params)
from app.models import EdgeDef, NodeDef, Workflow
from app.nodes import edit as edit_module
from app.nodes import generate as generate_module
from app.nodes.generate import GenerateImageNode
from app.nodes.transform import ResizeNode

# PNG 1x1 hợp lệ (PIL mở được — engine preview + node resize cần ảnh thật)
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415408d763f8cfc0f01f0005010100a5e3a4f70000000049454e44ae426082")


class StubProvider:
    """Ghi prompt + đếm số lần gọi để kiểm cache (không tốn token thật)."""

    def __init__(self):
        self.gen_calls = 0
        self.edit_calls = 0
        self.last_edit_prompt = None
        self.last_edit_labels = None

    def generate(self, prompt, **kw):
        self.gen_calls += 1
        return _PNG

    def edit(self, images, prompt, **kw):
        self.edit_calls += 1
        self.last_edit_prompt = prompt
        self.last_edit_labels = kw.get("image_labels")
        return _PNG


def _gen(nid, prompt, label=""):
    return NodeDef(id=nid, type="generate_image",
                   params={"provider": "cfg", "prompt": prompt, "image_label": label})


def _edit(nid, prompt):
    return NodeDef(id=nid, type="edit_image",
                   params={"provider": "cfg", "prompt": prompt})


def _edge(src, tgt, handle):
    return EdgeDef(source=src, sourceHandle="image", target=tgt, targetHandle=handle)


def _run(workflow, stub):
    """Patch resolve_model_config → stub trên module node, chạy workflow, khôi phục."""
    gen_orig = generate_module.resolve_model_config
    edit_orig = edit_module.resolve_model_config
    generate_module.resolve_model_config = lambda sel: (stub, "")
    edit_module.resolve_model_config = lambda sel: (stub, "")
    events = []

    async def emit(ev):
        events.append(ev)

    try:
        asyncio.run(run_workflow(workflow, emit))
    finally:
        generate_module.resolve_model_config = gen_orig
        edit_module.resolve_model_config = edit_orig
    errs = [e for e in events if e.type in ("node_error", "run_error")]
    assert not errs, f"workflow lỗi: {[e.message for e in errs]}"
    return events


# ---------- helper PURE (không cần engine) ----------

def test_key_params_excluding_labels():
    assert key_params_excluding_labels(
        {"prompt": "x", "image_label": "áo"}, {"image_label"}) == {"prompt": "x"}


def test_label_out_key_varies_with_label():
    assert label_out_key("k:image", "áo") != label_out_key("k:image", "người")
    assert label_out_key("k:image", "") == "k:image"
    assert label_out_key("k:image", "   ") == "k:image"  # khoảng trắng = rỗng


def test_label_params_from_class():
    assert label_params(GenerateImageNode) == {"image_label"}
    assert label_params(ResizeNode) == set()


# ---------- integration: đánh số + thứ tự ----------

def test_edit_prompt_numbers_images_in_order():
    with tempfile.TemporaryDirectory() as tmp:
        orig = cache.CACHE_DIR
        cache.CACHE_DIR = Path(tmp)
        try:
            stub = StubProvider()
            wf = Workflow(
                nodes=[_gen("g1", "áo", "cái áo"), _gen("g2", "người", "người mẫu"),
                       _edit("e", "ghép ảnh")],
                edges=[_edge("g1", "e", "image"), _edge("g2", "e", "images")])
            _run(wf, stub)
        finally:
            cache.CACHE_DIR = orig
        assert "Ảnh 1: cái áo" in stub.last_edit_prompt, stub.last_edit_prompt
        assert "Ảnh 2: người mẫu" in stub.last_edit_prompt, stub.last_edit_prompt


def test_engine_passes_image_labels_in_order():
    # Engine truyền image_labels (song song images) để provider xen caption từng ảnh
    with tempfile.TemporaryDirectory() as tmp:
        orig = cache.CACHE_DIR
        cache.CACHE_DIR = Path(tmp)
        try:
            stub = StubProvider()
            wf = Workflow(
                nodes=[_gen("g1", "áo", "cái áo"), _gen("g2", "người", "người mẫu"),
                       _edit("e", "ghép ảnh")],
                edges=[_edge("g1", "e", "image"), _edge("g2", "e", "images")])
            _run(wf, stub)
        finally:
            cache.CACHE_DIR = orig
        assert stub.last_edit_labels == ["cái áo", "người mẫu"], stub.last_edit_labels


def test_edit_prompt_has_identity_instruction():
    # Có nhãn → chèn chỉ thị giữ nhận dạng (chống tráo mặt)
    from app.nodes.image_label_block import IMAGE_REF_INSTRUCTION
    with tempfile.TemporaryDirectory() as tmp:
        orig = cache.CACHE_DIR
        cache.CACHE_DIR = Path(tmp)
        try:
            stub = StubProvider()
            wf = Workflow(
                nodes=[_gen("g1", "áo", "cái áo"), _edit("e", "ghép ảnh")],
                edges=[_edge("g1", "e", "image")])
            _run(wf, stub)
        finally:
            cache.CACHE_DIR = orig
        assert IMAGE_REF_INSTRUCTION in stub.last_edit_prompt, stub.last_edit_prompt


# ---------- integration: cache (đổi mô tả không tốn token) ----------

def test_change_label_cache_hit_source_rerun_edit():
    with tempfile.TemporaryDirectory() as tmp:
        orig = cache.CACHE_DIR
        cache.CACHE_DIR = Path(tmp)
        try:
            stub = StubProvider()
            nodes1 = [_gen("g1", "áo", "cái áo"), _gen("g2", "người", "người mẫu"),
                      _edit("e", "ghép ảnh")]
            edges = [_edge("g1", "e", "image"), _edge("g2", "e", "images")]
            _run(Workflow(nodes=nodes1, edges=edges), stub)
            gen_after_run1 = stub.gen_calls
            edit_after_run1 = stub.edit_calls

            # Đổi mô tả gen1 (prompt giữ nguyên) → chạy lại
            nodes2 = [_gen("g1", "áo", "áo khoác"), _gen("g2", "người", "người mẫu"),
                      _edit("e", "ghép ảnh")]
            _run(Workflow(nodes=nodes2, edges=edges), stub)
        finally:
            cache.CACHE_DIR = orig
        # Node nguồn cache-hit → KHÔNG gọi lại generate (không tốn token)
        assert stub.gen_calls == gen_after_run1, "đổi mô tả KHÔNG được sinh lại ảnh AI"
        # Node Sửa ảnh chạy lại (prompt đổi)
        assert stub.edit_calls > edit_after_run1, "node Sửa ảnh phải chạy lại"
        assert "áo khoác" in stub.last_edit_prompt, stub.last_edit_prompt


# ---------- integration: passthrough qua node Biến đổi ----------

def test_label_passthrough_resize():
    with tempfile.TemporaryDirectory() as tmp:
        orig = cache.CACHE_DIR
        cache.CACHE_DIR = Path(tmp)
        try:
            stub = StubProvider()
            wf = Workflow(
                nodes=[_gen("g1", "áo", "cái áo"),
                       NodeDef(id="r", type="resize",
                               params={"width": 64, "height": 64, "keep_aspect": True}),
                       _edit("e", "ghép ảnh")],
                edges=[_edge("g1", "r", "image"), _edge("r", "e", "image")])
            _run(wf, stub)
        finally:
            cache.CACHE_DIR = orig
        assert "Ảnh 1: cái áo" in stub.last_edit_prompt, stub.last_edit_prompt


# ---------- integration: backward compat (không nhãn) ----------

def test_no_label_prompt_unchanged():
    with tempfile.TemporaryDirectory() as tmp:
        orig = cache.CACHE_DIR
        cache.CACHE_DIR = Path(tmp)
        try:
            stub = StubProvider()
            wf = Workflow(
                nodes=[_gen("g1", "áo"), _edit("e", "ghép ảnh")],
                edges=[_edge("g1", "e", "image")])
            _run(wf, stub)
        finally:
            cache.CACHE_DIR = orig
        assert "Ảnh đầu vào:" not in stub.last_edit_prompt, stub.last_edit_prompt
        assert stub.last_edit_prompt == "ghép ảnh", stub.last_edit_prompt


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL  {fn.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    raise SystemExit(0 if passed == len(tests) else 1)
