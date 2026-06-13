"""Test FakeProvider + đăng ký provider (Phase 4) — offline, không mạng.

Chạy: backend\\.venv\\Scripts\\python.exe test_fake_provider.py
"""
import io

from PIL import Image

from app import providers
from app.providers import PROVIDER_NAMES, make_provider, resolve_model_config
from app.providers.fake import FakeProvider


def test_generate_returns_png():
    data = FakeProvider().generate("mèo phi hành gia")
    img = Image.open(io.BytesIO(data))
    assert img.format == "PNG"
    assert img.mode in ("RGB", "RGBA")


def test_edit_uses_base():
    base = FakeProvider().generate("nền gốc")
    out = FakeProvider().edit([base], "đổi nền thành sao Hỏa")
    Image.open(io.BytesIO(out))  # mở được = PNG hợp lệ


def test_edit_no_base():
    out = FakeProvider().edit([], "tạo từ trống")
    Image.open(io.BytesIO(out))


def test_generate_text_prefix():
    assert FakeProvider().generate_text("xin chào").startswith("[fake]")


def test_make_provider_fake():
    assert isinstance(make_provider("fake"), FakeProvider)
    assert "fake" in PROVIDER_NAMES


def test_force_fake_resolves_fake():
    providers.FORCE_FAKE = True
    try:
        prov, model = resolve_model_config("cấu hình không tồn tại")
        assert isinstance(prov, FakeProvider)
        assert model == ""
    finally:
        providers.FORCE_FAKE = False


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            import traceback
            print(f"  FAIL  {fn.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} tests passed")
    raise SystemExit(0 if passed == len(tests) else 1)
