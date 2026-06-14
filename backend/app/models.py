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
    # ...| harness_iteration (1 vòng critic) | harness_report (tổng kết best)
    type: str  # run_started | node_started | node_finished | node_error | run_finished | run_error
    node_id: Optional[str] = None
    message: Optional[str] = None
    preview: Optional[str] = None  # base64 PNG thumbnail
    outputs: Optional[dict[str, Any]] = None
    cached: bool = False  # node_finished dùng output cache (không thực thi lại)
    # Harness loop (chỉ ở event harness_*):
    iteration: Optional[int] = None       # số thứ tự vòng (0-based)
    score: Optional[float] = None         # điểm critic 0..10
    passed: Optional[bool] = None         # vòng này đạt ngưỡng chưa
    report: Optional[dict[str, Any]] = None  # harness_report: best_iteration/best_score/history


class HarnessConfig(BaseModel):
    """Bật chế độ harness critic-refine loop. Thiếu/`enabled=false` → chạy thường."""
    enabled: bool = False
    max_iterations: int = Field(default=3, ge=1, le=20)  # chặn loop vô hạn ở biên
    criteria: str = ""          # tiêu chí đạt (tùy chọn); trống → chấm theo goal
    pass_score: float = Field(default=8.0, ge=0, le=10)  # ngưỡng điểm coi là "đạt"
    critic_provider: str = ""   # cấu hình model vision để chấm; trống → dùng provider node sinh


class RunRequest(BaseModel):
    """Envelope chạy workflow: target (chạy tới node) + force (ép chạy lại)."""
    workflow: Workflow
    target: Optional[str] = None
    force: list[str] = Field(default_factory=list)
    harness: Optional[HarnessConfig] = None
