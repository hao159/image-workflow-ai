"""Khóa cache địa chỉ-nội-dung cho engine (Merkle / key-propagation).

Mỗi node có `node_key = sha256(type + params + parent_output_keys + code_hash)`.
Đổi param / input / code của một node → key đổi → lan xuống downstream (vì
output_key của node nằm trong `inputs` khi tính key của node con). Nhánh không
đổi giữ nguyên key → cache-hit. KHÔNG hash lại bytes ảnh (chỉ hash địa chỉ).
"""
import hashlib
import inspect
import json
from collections import defaultdict, deque

# Cache source-hash theo class node (inspect.getsource hơi chậm, gọi mỗi node/run).
_CODE_HASH_CACHE: dict[type, str] = {}


def code_hash(cls) -> str:
    """sha256 (16 hex) của source code CLASS node. Sửa code node → cache tự vô hiệu.

    Chỉ băm chính class — helper/dependency của node KHÔNG được băm, nên sửa helper
    phải 🗑 Xóa cache thủ công. Class định nghĩa động (vd trong test) có thể không
    lấy được source → code rỗng (an toàn, key vẫn xác định theo type+params).
    """
    cached = _CODE_HASH_CACHE.get(cls)
    if cached is not None:
        return cached
    try:
        src = inspect.getsource(cls)
    except (OSError, TypeError):
        src = ""
    digest = hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]
    _CODE_HASH_CACHE[cls] = digest
    return digest


def node_key(node_type: str, params: dict, inputs_out_keys: dict, code: str) -> str:
    """Khóa xác định (deterministic) của một node.

    `inputs_out_keys`: {target_handle: [output_key của từng dây nối vào, ...]}.
    """
    payload = {"type": node_type, "params": params,
               "inputs": inputs_out_keys, "code": code}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def label_params(cls) -> set[str]:
    """Tên các param đánh dấu is_image_label trên class node (vd 'image_label')."""
    return {p.name for p in getattr(cls, "params", [])
            if getattr(p, "is_image_label", False)}


def key_params_excluding_labels(params: dict, label_names: set[str]) -> dict:
    """params để tính node_key — đã bỏ param nhãn.

    Nhờ vậy đổi mô tả ảnh ≠ đổi node_key → node giữ nhãn cache-hit (không sinh lại
    ảnh AI = không tốn token). Nhãn lan xuống downstream qua output_key (label_out_key).
    """
    return {k: v for k, v in params.items() if k not in label_names}


def label_out_key(base_out_key: str, label: str) -> str:
    """output_key của ảnh, nối hash nhãn → node con thấy in_key đổi khi nhãn đổi.

    Nhãn rỗng/khoảng trắng → giữ nguyên key (backward compat, không phình key).
    """
    if not (label or "").strip():
        return base_out_key
    h = hashlib.sha256(label.strip().encode("utf-8")).hexdigest()[:8]
    return f"{base_out_key}#{h}"


def prune_to_ancestors(order: list[str], target: str, edges) -> list[str]:
    """Giữ lại `target` + mọi tổ tiên của nó, theo đúng thứ tự topo gốc.

    Dùng cho "chạy tới node này": chỉ thực thi node + những gì nó phụ thuộc.
    """
    parents: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        parents[e.target].append(e.source)
    keep: set[str] = set()
    queue = deque([target])
    while queue:
        nid = queue.popleft()
        if nid in keep:
            continue
        keep.add(nid)
        for parent in parents[nid]:
            if parent not in keep:
                queue.append(parent)
    return [nid for nid in order if nid in keep]
