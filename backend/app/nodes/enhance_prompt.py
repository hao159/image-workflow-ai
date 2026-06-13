from ..providers import provider_options, resolve_model_config
from .base import BaseNode, Param, Port, register_node
from .prompt_merge import merge_prompt

# Số từ mục tiêu cho từng mức chi tiết của prompt sau khi enhance
DETAIL_LEVELS = {"ngắn": 40, "vừa": 80, "dài": 150}

SYSTEM_INSTRUCTION = (
    "You are a prompt engineer for AI image generation. Rewrite the user's prompt "
    "into one vivid, detailed image-generation prompt in English covering: subject, "
    "composition, lighting, materials/textures, colors, mood, and style. "
    "Preserve the user's intent exactly — do not add unrelated subjects or change "
    "the requested style. Aim for about {words} words. "
    "Return ONLY the rewritten prompt text: no quotes, no preamble, no explanation."
)


@register_node
class EnhancePromptNode(BaseNode):
    type_name = "enhance_prompt"
    title = "Enhance prompt (AI)"
    category = "AI"
    description = ("Dùng AI viết lại prompt chi tiết, giàu mô tả hơn rồi đưa sang "
                   "node Tạo ảnh / Sửa ảnh. Prompt gốc lấy từ cổng vào nếu được nối, "
                   "không thì dùng prompt gõ trong node.")
    inputs = [Port("text", "text", "Prompt gốc", required=False)]
    outputs = [Port("text", "text", "Prompt đã enhance")]
    params = [
        Param("provider", "select", "Model / Provider", default="",
              dynamic_options=provider_options),
        Param("prompt", "textarea", "Prompt gốc", default="",
              supplement_for="text", supplement_label="Prompt bổ sung"),
        Param("style", "textarea", "Hướng dẫn thêm (tùy chọn)", default=""),
        Param("detail", "select", "Mức chi tiết", default="vừa",
              options=list(DETAIL_LEVELS)),
    ]

    def run(self, inputs, params):
        prompt = merge_prompt(inputs.get("text"), params.get("prompt"))
        if not prompt.strip():
            raise ValueError(
                "Node 'Enhance prompt' cần prompt gốc (nối vào cổng hoặc gõ trực tiếp).")
        provider, default_model = resolve_model_config(params["provider"])

        words = DETAIL_LEVELS.get(params.get("detail") or "vừa", 80)
        system = SYSTEM_INSTRUCTION.format(words=words)
        style = (params.get("style") or "").strip()
        if style:
            system += f" Additional style guidance from the user: {style}"

        enhanced = provider.generate_text(prompt, model=default_model, system=system)
        return {"text": enhanced}
