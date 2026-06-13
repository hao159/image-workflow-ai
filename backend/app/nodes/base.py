from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Port:
    name: str
    dtype: str  # "image" | "text"
    label: str = ""
    required: bool = True
    # True = cổng nhận nhiều dây; node sẽ nhận list giá trị theo thứ tự nối
    multiple: bool = False

    def to_dict(self) -> dict:
        return {"name": self.name, "dtype": self.dtype,
                "label": self.label or self.name, "required": self.required,
                "multiple": self.multiple}


@dataclass
class Param:
    name: str
    ptype: str  # "text" | "textarea" | "number" | "select" | "image_upload" | "checkbox"
    label: str = ""
    default: Any = None
    options: list[str] = field(default_factory=list)
    min: float | None = None
    max: float | None = None
    step: float | None = None
    # options tính tại lúc gọi /api/node-types (vd: danh sách cấu hình model trong DB)
    dynamic_options: Callable[[], list[str]] | None = None
    # Tên cổng input mà param này "bổ sung": khi cổng đó được nối dây, giá trị
    # nối vào được ghép với giá trị param (xem prompt_merge.merge_prompt). UI dùng
    # để đổi nhãn param sang supplement_label + báo cổng đã nối.
    supplement_for: str | None = None
    supplement_label: str = ""
    # True = ô "Mô tả ảnh" trên node nguồn: vừa làm phụ đề node (frontend), vừa
    # đi theo ảnh xuống node "Sửa ảnh" để engine chèn khối tham chiếu "Ảnh N".
    # KHÔNG tính vào node_key (đổi mô tả không sinh lại ảnh AI — xem engine).
    is_image_label: bool = False

    def to_dict(self) -> dict:
        options = self.dynamic_options() if self.dynamic_options else self.options
        default = self.default
        if self.dynamic_options and options:
            default = options[0]
        d = {"name": self.name, "ptype": self.ptype,
             "label": self.label or self.name, "default": default}
        # Param dynamic luôn xuất "options" (kể cả rỗng) để frontend không vỡ
        # khi chưa có cấu hình nào (select.options.map trên undefined).
        if self.dynamic_options:
            d["options"] = options or []
        elif options:
            d["options"] = options
        for k in ("min", "max", "step"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        if self.supplement_for:
            d["supplement_for"] = self.supplement_for
            d["supplement_label"] = self.supplement_label or self.label or self.name
        if self.is_image_label:
            d["is_image_label"] = True
        return d


NODE_REGISTRY: dict[str, type["BaseNode"]] = {}


def register_node(cls: type["BaseNode"]) -> type["BaseNode"]:
    NODE_REGISTRY[cls.type_name] = cls
    return cls


class BaseNode:
    type_name: str = ""
    title: str = ""
    category: str = "Khác"
    description: str = ""
    inputs: list[Port] = []
    outputs: list[Port] = []
    params: list[Param] = []
    # Nhãn (mô tả ảnh) của từng cổng input ảnh, engine set trước khi gọi run():
    # {handle: [nhãn theo thứ tự cạnh nối]}. Mặc định rỗng → node chạy như cũ.
    input_labels: dict = {}
    # Tên cổng input mà output ảnh KẾ THỪA nhãn (passthrough): node "Biến đổi"
    # (resize/filter/adjust) đặt = "image" → nhãn ảnh vào sống sót qua node.
    # None = không kế thừa (vd edit_image: output là ảnh ghép, không nhãn).
    label_passthrough_from: str | None = None

    @classmethod
    def metadata(cls) -> dict:
        return {
            "type": cls.type_name,
            "title": cls.title,
            "category": cls.category,
            "description": cls.description,
            "inputs": [p.to_dict() for p in cls.inputs],
            "outputs": [p.to_dict() for p in cls.outputs],
            "params": [p.to_dict() for p in cls.params],
        }

    @classmethod
    def resolve_params(cls, raw: dict) -> dict:
        merged = {p.name: p.default for p in cls.params}
        merged.update({k: v for k, v in raw.items() if v is not None})
        return merged

    def run(self, inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Chạy đồng bộ trong thread pool. Trả về dict {tên_output: giá_trị}.

        Giá trị image là bytes (PNG), text là str.
        """
        raise NotImplementedError
