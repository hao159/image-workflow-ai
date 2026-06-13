def merge_prompt(connected: str | None, supplement: str | None, sep: str = ", ") -> str:
    """Ghép prompt từ cổng nối + prompt bổ sung gõ trong node.

    Lọc phần rỗng; phần nối vào đặt trước, phần bổ sung đặt sau.
    - Cả hai có giá trị  -> "<connected><sep><supplement>"
    - Chỉ nối (ô rỗng)   -> "<connected>"
    - Chỉ gõ (không nối) -> "<supplement>"  (giữ hành vi nhập trực tiếp)
    - Cả hai rỗng        -> ""
    """
    return sep.join(p.strip() for p in (connected, supplement) if p and p.strip())
