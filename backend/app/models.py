from typing import Any, Optional

from pydantic import BaseModel, Field


class NodeDef(BaseModel):
    id: str
    type: str
    params: dict[str, Any] = Field(default_factory=dict)
    position: dict[str, float] = Field(default_factory=dict)


class EdgeDef(BaseModel):
    id: Optional[str] = None
    source: str
    sourceHandle: Optional[str] = None
    target: str
    targetHandle: Optional[str] = None


class Workflow(BaseModel):
    name: str = "untitled"
    nodes: list[NodeDef]
    edges: list[EdgeDef]


class RunEvent(BaseModel):
    type: str  # run_started | node_started | node_finished | node_error | run_finished | run_error
    node_id: Optional[str] = None
    message: Optional[str] = None
    preview: Optional[str] = None  # base64 PNG thumbnail
    outputs: Optional[dict[str, Any]] = None
    cached: bool = False  # node_finished dùng output cache (không thực thi lại)


class RunRequest(BaseModel):
    """Envelope chạy workflow: target (chạy tới node) + force (ép chạy lại)."""
    workflow: Workflow
    target: Optional[str] = None
    force: list[str] = Field(default_factory=list)
