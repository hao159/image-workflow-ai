from ..providers import provider_options, resolve_model_config
from .base import BaseNode, Param, Port, register_node
from .prompt_merge import merge_prompt

ASPECT_RATIOS = ["1:1", "16:9", "9:16", "3:2", "2:3", "4:3", "3:4"]


@register_node
class GenerateImageNode(BaseNode):
    type_name = "generate_image"
    title = "Tạo ảnh (AI)"
    category = "AI"
    description = ("Tạo ảnh từ prompt. Prompt lấy từ cổng vào nếu được nối, "
                   "không thì dùng prompt gõ trong node.")
    inputs = [Port("prompt", "text", "Prompt", required=False)]
    outputs = [Port("image", "image", "Ảnh")]
    params = [
        Param("provider", "select", "Model / Provider", default="",
              dynamic_options=provider_options),
        Param("prompt", "textarea", "Prompt", default="",
              supplement_for="prompt", supplement_label="Prompt bổ sung"),
        Param("aspect_ratio", "select", "Tỷ lệ khung", default="1:1", options=ASPECT_RATIOS),
        Param("negative_prompt", "textarea", "Negative prompt (ComfyUI)", default=""),
        Param("image_label", "text", "Mô tả ảnh", default="", is_image_label=True),
    ]

    def run(self, inputs, params):
        prompt = merge_prompt(inputs.get("prompt"), params.get("prompt"))
        if not prompt.strip():
            raise ValueError("Node 'Tạo ảnh' cần prompt (nối vào cổng hoặc gõ trực tiếp).")
        provider, default_model = resolve_model_config(params["provider"])
        image = provider.generate(
            prompt,
            model=default_model,
            aspect_ratio=params.get("aspect_ratio") or "1:1",
            negative_prompt=params.get("negative_prompt") or "",
        )
        return {"image": image}
