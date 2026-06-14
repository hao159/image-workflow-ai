"""Khối tham chiếu "Ảnh N" ghép vào prompt node "Sửa ảnh" (pure, không engine).

Mô tả ảnh trên node nguồn đi theo ảnh xuống node "Sửa ảnh"; engine gom nhãn
theo đúng thứ tự ảnh rồi gọi compose_edit_prompt() để AI biết "Ảnh 1/2/3" là gì.
Tách riêng để test thẳng, không cần chạy server/provider.
"""

REFERENCE_HEADER = "Ảnh đầu vào:"
NO_LABEL = "(không mô tả)"
# Chỉ thị giữ nhận dạng — chống lỗi model bốc nhầm mặt nguồn vào sai vị trí
# (tên đúng nhưng mặt sai). Chỉ chèn khi có nhãn (đa-ảnh có mô tả).
IMAGE_REF_INSTRUCTION = (
    "Dùng đúng người/khuôn mặt từ mỗi ảnh nguồn liệt kê ở trên; "
    "giữ nguyên nhận dạng từng người, KHÔNG tráo mặt giữa các ảnh.")


def build_reference_block(labels: list[str]) -> str:
    """Dựng khối liệt kê "Ảnh N: <mô tả>" từ list nhãn theo đúng thứ tự ảnh.

    index 0 = Ảnh 1. Nhãn rỗng/khoảng trắng → "(không mô tả)" (số KHÔNG nhảy).
    Trả "" nếu KHÔNG nhãn nào có nội dung → prompt giữ nguyên (backward compat).
    """
    if not any((l or "").strip() for l in labels):
        return ""
    lines = [f"- Ảnh {i + 1}: {(l or '').strip() or NO_LABEL}" for i, l in enumerate(labels)]
    return REFERENCE_HEADER + "\n" + "\n".join(lines)


def compose_edit_prompt(labels: list[str], prompt: str,
                        instruction_override: str | None = None) -> str:
    """Ghép khối tham chiếu + chỉ thị giữ nhận dạng (nếu có nhãn) TRƯỚC prompt.

    Không nhãn nào → trả prompt y như cũ (backward compat). Đây là cách trình bày
    dạng-text dùng cho provider KHÔNG xen kẽ được ảnh (OpenAI Images-Edit, ComfyUI);
    Codex/Gemini còn xen caption ngay trước từng ảnh (xem provider).

    `instruction_override`: chỉ thị do user nhập trên node → ĐÈ chỉ thị identity mặc
    định. Rỗng/khoảng trắng/None → giữ mặc định (giữ hành vi cũ khi có nhãn)."""
    block = build_reference_block(labels)
    if not block:
        return prompt
    instruction = (instruction_override or "").strip() or IMAGE_REF_INSTRUCTION
    return f"{block}\n{instruction}\n\n{prompt}"
