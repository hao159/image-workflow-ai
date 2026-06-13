"""Test chuẩn hóa ảnh upload: resize ≤ 2048px + nén + guard kích thước/định dạng.

Chạy: backend\\.venv\\Scripts\\python.exe test_image_normalize.py
"""
import io

from PIL import Image

from app import image_normalize as N
from app.image_normalize import MAX_DIMENSION, normalize_image


def _img_bytes(w, h, mode="RGB"):
    color = (120, 60, 30, 255) if mode == "RGBA" else (120, 60, 30)
    buf = io.BytesIO()
    Image.new(mode, (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


def test_downscale_large_to_cap():
    out, ext = normalize_image(_img_bytes(3000, 2000))
    im = Image.open(io.BytesIO(out))
    assert max(im.size) == MAX_DIMENSION  # cạnh dài đúng cap 2048
    assert ext == "jpg"  # không alpha → JPEG


def test_small_image_not_upscaled():
    out, _ = normalize_image(_img_bytes(100, 80))
    im = Image.open(io.BytesIO(out))
    assert im.size == (100, 80)  # KHÔNG phóng to ảnh nhỏ


def test_alpha_kept_as_png():
    out, ext = normalize_image(_img_bytes(50, 50, mode="RGBA"))
    assert ext == "png"
    assert Image.open(io.BytesIO(out)).mode == "RGBA"  # giữ trong suốt


def test_invalid_bytes_raises():
    try:
        normalize_image(b"day khong phai anh")
    except ValueError:
        pass
    else:
        raise AssertionError("bytes không phải ảnh phải raise ValueError")


def test_oversize_raises():
    orig = N.MAX_UPLOAD_BYTES
    N.MAX_UPLOAD_BYTES = 10
    try:
        normalize_image(b"x" * 100)
    except ValueError:
        pass
    else:
        raise AssertionError("vượt MAX_UPLOAD_BYTES phải raise ValueError")
    finally:
        N.MAX_UPLOAD_BYTES = orig


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
