"""Chuẩn hóa ảnh upload trước khi lưu: thu nhỏ + nén để chặn file vài chục MB.

Áp ở upload-time → bao luôn lúc truyền cho provider AI (base64 nhỏ đi, cache gọn).
Pure, không phụ thuộc engine/server → test thẳng bằng PIL.
"""
import io

from PIL import Image, ImageOps

# Cạnh dài tối đa: 2048 cân bằng dung lượng (~1–2MB) và chi tiết mặt cho ghép người.
MAX_DIMENSION = 2048
JPEG_QUALITY = 85
# Chặn cứng file thô trước khi decode — chống OOM / decompression-bomb.
MAX_UPLOAD_BYTES = 40 * 1024 * 1024


def normalize_image(data: bytes) -> tuple[bytes, str]:
    """Trả (bytes ảnh đã chuẩn hóa, đuôi 'png'|'jpg').

    - Cạnh dài > MAX_DIMENSION → thu nhỏ giữ tỉ lệ (LANCZOS); ảnh nhỏ KHÔNG phóng to.
    - Áp orientation EXIF rồi bỏ metadata (ảnh điện thoại không bị xoay sai).
    - Có alpha → PNG (optimize, giữ trong suốt cho khung); không → JPEG q85 (nhẹ hơn nhiều).
    Raise ValueError nếu file quá lớn hoặc không decode được ảnh.
    """
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Ảnh quá lớn (> {MAX_UPLOAD_BYTES // (1024 * 1024)}MB).")
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)  # decode + áp xoay; raise nếu ảnh hỏng/bomb
    except Exception as e:  # noqa: BLE001 — gộp mọi lỗi decode thành lỗi rõ cho UI
        raise ValueError(f"File không phải ảnh hợp lệ: {e}") from e

    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    has_alpha = img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info)
    buf = io.BytesIO()
    if has_alpha:
        img.convert("RGBA").save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "png"
    img.convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue(), "jpg"
