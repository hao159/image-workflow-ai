from .base import BaseNode, NODE_REGISTRY, register_node
from . import inputs, generate, edit, enhance_prompt, transform, output  # noqa: F401 — đăng ký node


def get_node_class(type_name: str) -> type[BaseNode]:
    if type_name not in NODE_REGISTRY:
        raise ValueError(f"Không có loại node: {type_name}")
    return NODE_REGISTRY[type_name]


def node_type_metadata() -> list[dict]:
    return [cls.metadata() for cls in NODE_REGISTRY.values()]
