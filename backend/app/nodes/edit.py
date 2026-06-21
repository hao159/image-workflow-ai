from ..providers import provider_options, resolve_model_config
from .base import BaseNode, Param, Port, register_node
from .image_label_block import compose_edit_prompt
from .prompt_merge import merge_prompt


@register_node
class EditImageNode(BaseNode):
    type_name = "edit_image"
    title = "Sửa ảnh (AI)"
    category = "AI"
    description = ("Sửa/ghép ảnh theo prompt: đổi nền, thêm/bớt chi tiết, đổi style... "
                   "Cổng 'Ảnh ghép thêm' nhận nhiều dây — nối bao nhiêu ảnh cũng được.")
    inputs = [
        Port("image", "image", "Ảnh gốc"),
        Port("images", "image", "Ảnh ghép thêm", required=False, multiple=True),
        Port("prompt", "text", "Prompt", required=False),
    ]
    outputs = [Port("image", "image", "Ảnh")]
    params = [
        Param("provider", "select", "Model / Provider", default="",
              dynamic_options=provider_options),
        Param("prompt", "textarea", "Prompt sửa ảnh", default="",
              supplement_for="prompt", supplement_label="Prompt bổ sung"),
        # Đè chỉ thị identity mặc định (khối "Ảnh N") khi cần ý đồ khác face-swap.
        # Trống → giữ chỉ thị mặc định (backward compat). Chỉ tác dụng khi có nhãn ảnh.
        Param("instruction", "textarea", "Chỉ thị hệ thống (tùy chọn)", default=""),
    ]

    def run(self, inputs, params):
        image = inputs.get("image")
        if not image:
            raise ValueError("Node 'Sửa ảnh' cần ảnh đầu vào.")
        prompt = merge_prompt(inputs.get("prompt"), params.get("prompt"))
        if not prompt.strip():
            raise ValueError("Node 'Sửa ảnh' cần prompt mô tả thay đổi.")
        images = [image, *(inputs.get("images") or [])]
        if inputs.get("image2"):  # tương thích workflow lưu trước khi có cổng multiple
            images.append(inputs["image2"])
        # Nhãn theo ĐÚNG thứ tự ảnh để khối "Ảnh N" khớp ảnh nào là gì. engine set
        # self.input_labels = {handle: [nhãn theo cạnh]}; mặc định {} → labels rỗng
        # → compose_edit_prompt trả prompt y như cũ (backward compat).
        il = self.input_labels
        labels = [(il.get("image") or [""])[-1]]
        labels += list(il.get("images") or [])
        if inputs.get("image2"):
            labels.append((il.get("image2") or [""])[-1])
        prompt = compose_edit_prompt(labels, prompt,
                                     instruction_override=params.get("instruction"))
        provider, default_model = resolve_model_config(params["provider"])
        # image_labels (song song images) cho provider xen caption trước từng ảnh
        # (Codex/Gemini). Provider không hỗ trợ (OpenAI) bỏ qua qua **options.
        result = provider.edit(
            images, prompt,
            model=default_model,
            image_labels=labels,
        )
        return {"image": result}
