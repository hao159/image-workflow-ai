"""Test node Trích vùng (AI): vision trả bbox 0..1 → crop PIL (giữ pixel gốc).

Test thuần Python — KHÔNG cần server/token. Provider thay bằng stub qua monkeypatch
app.nodes.extract_region.resolve_model_config.

Chạy: backend\\.venv\\Scripts\\python.exe test_extract_region.py
"""
import io

from PIL import Image

from app.nodes import extract_region as er_module
from app.nodes.extract_region import ExtractRegionNode, crop_region
from app.providers.base import ImageProvider, ProviderError, parse_bbox_json


def _png(w, h, color=(120, 80, 200)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


def _size(data):
    return Image.open(io.BytesIO(data)).size


class BBoxStub:
    """Provider stub trả bbox cố định (giả vision)."""

    def __init__(self, bbox):
        self.bbox = bbox
        self.calls = 0
        self.last_target = None

    def detect_region(self, image, target, *, model="", **kw):
        self.calls += 1
        self.last_target = target
        return self.bbox


def _run(stub, params, image=None):
    orig = er_module.resolve_model_config
    er_module.resolve_model_config = lambda sel: (stub, "")
    try:
        return ExtractRegionNode().run({"image": image or _png(100, 100)}, params)
    finally:
        er_module.resolve_model_config = orig


# ---------- crop_region (pure) ----------

def test_crop_basic_half():
    out = crop_region(_png(100, 100), [0.25, 0.25, 0.75, 0.75], 0.0)
    assert _size(out) == (50, 50), _size(out)


def test_crop_padding_expands():
    # box 50x50 (px), padding 0.1 → +5px mỗi cạnh → 60x60
    out = crop_region(_png(100, 100), [0.25, 0.25, 0.75, 0.75], 0.1)
    assert _size(out) == (60, 60), _size(out)


def test_crop_padding_clamps_to_image():
    # box sát mép + padding lớn → clamp trong khung, không vượt
    out = crop_region(_png(100, 100), [0.0, 0.0, 1.0, 1.0], 0.5)
    assert _size(out) == (100, 100), _size(out)


def test_crop_invalid_bbox_raises():
    for bad in ([0.5, 0.5, 0.2, 0.2], [0, 0, 1.5, 1], [0.1, 0.2, 0.3]):
        try:
            crop_region(_png(100, 100), bad, 0.0)
            assert False, f"bbox {bad} phải lỗi"
        except (ValueError, ProviderError):
            pass


# ---------- node run ----------

def test_node_crops_with_stub():
    stub = BBoxStub([0.25, 0.25, 0.75, 0.75])
    out = _run(stub, {"provider": "cfg", "target": "con bò", "padding": 0.0})
    assert _size(out["image"]) == (50, 50)
    assert stub.last_target == "con bò"


def test_node_requires_target():
    stub = BBoxStub([0.1, 0.1, 0.9, 0.9])
    try:
        _run(stub, {"provider": "cfg", "target": "", "padding": 0.0})
        assert False, "thiếu target phải lỗi"
    except ValueError:
        pass


def test_node_provider_without_detect_region_errors():
    # Provider mặc định (base) không hỗ trợ → ProviderError rõ
    class PlainProvider(ImageProvider):
        name = "plain"

        def generate(self, prompt, **kw):
            return b""

        def edit(self, images, prompt, **kw):
            return b""

    try:
        _run(PlainProvider(), {"provider": "cfg", "target": "mèo", "padding": 0.0})
        assert False, "provider không hỗ trợ detect_region phải lỗi"
    except ProviderError as e:
        assert "trích vùng" in str(e) or "detect" in str(e).lower()


# ---------- parse helpers (pure, dùng chung gemini + openai) ----------

def test_parse_bbox_normalized():
    assert parse_bbox_json('{"found":true,"box":[0.1,0.2,0.3,0.4]}', scale=1.0) == [0.1, 0.2, 0.3, 0.4]


def test_parse_bbox_scaled_999():
    out = parse_bbox_json('{"found":true,"box":[100,200,400,600]}', scale=999.0)
    assert abs(out[0] - 100 / 999) < 1e-6 and abs(out[3] - 600 / 999) < 1e-6


def test_parse_bbox_strips_fences():
    out = parse_bbox_json('```json\n{"found":true,"box":[0,0,1,1]}\n```', scale=1.0)
    assert out == [0.0, 0.0, 1.0, 1.0]


def test_parse_bbox_not_found_or_invalid_raises():
    for t in ['{"found":false}', '{"box":null}', 'garbage', '{"found":true,"box":[0,0,1]}']:
        try:
            parse_bbox_json(t, scale=1.0, target="mèo")
            assert False, f"{t} phải lỗi"
        except ProviderError:
            pass


def test_node_params_present():
    params = {p["name"]: p for p in ExtractRegionNode.metadata()["params"]}
    assert "target" in params and "provider" in params
    assert params.get("image_label", {}).get("is_image_label") is True


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
