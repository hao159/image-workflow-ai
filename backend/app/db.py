"""SQLite lưu cấu hình model (API key đặt tên) và workflow đã lưu."""
import json
import sqlite3
from contextlib import contextmanager

from . import config


@contextmanager
def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        with conn:  # tự commit/rollback
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS model_configs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                provider   TEXT NOT NULL,
                api_key    TEXT NOT NULL DEFAULT '',
                model      TEXT NOT NULL DEFAULT '',
                base_url   TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS workflows (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                data       TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_name TEXT NOT NULL,
                mode          TEXT NOT NULL DEFAULT 'full',  -- full|harness
                status        TEXT NOT NULL,                 -- running|success|error|stopped
                error         TEXT NOT NULL DEFAULT '',
                detail        TEXT NOT NULL DEFAULT '{}',    -- JSON: {nodes, harness, output_refs}
                started_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                finished_at   TEXT,
                duration_ms   INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_exec_wf
                ON workflow_executions(workflow_name, id DESC);
        """)
    _migrate_json_workflows()


def _migrate_json_workflows() -> None:
    """Nhập một lần các workflow .json cũ trong thư mục workflows/ vào DB."""
    for path in sorted(config.WORKFLOWS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = data.get("name") or path.stem
        with _connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO workflows (name, data) VALUES (?, ?)",
                (name, json.dumps(data, ensure_ascii=False)),
            )


# ---------- Cấu hình model (API key đặt tên) ----------

def list_model_configs() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM model_configs ORDER BY created_at, id").fetchall()
    return [dict(r) for r in rows]


def get_model_config(name: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM model_configs WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def get_model_config_by_id(config_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM model_configs WHERE id = ?", (config_id,)).fetchone()
    return dict(row) if row else None


def save_model_config(name: str, provider: str, api_key: str, model: str,
                      base_url: str, config_id: int | None = None) -> int | None:
    """Tạo mới hoặc cập nhật; trả về id, hoặc None nếu id cần cập nhật không tồn tại."""
    with _connect() as conn:
        if config_id is not None:
            if api_key == "":  # để trống = giữ key cũ
                cur = conn.execute(
                    "UPDATE model_configs SET name=?, provider=?, model=?, base_url=? WHERE id=?",
                    (name, provider, model, base_url, config_id))
            else:
                cur = conn.execute(
                    "UPDATE model_configs SET name=?, provider=?, api_key=?, model=?, base_url=? WHERE id=?",
                    (name, provider, api_key, model, base_url, config_id))
            return config_id if cur.rowcount else None
        cur = conn.execute(
            "INSERT INTO model_configs (name, provider, api_key, model, base_url) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, provider, api_key, model, base_url))
        return cur.lastrowid


def delete_model_config(config_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM model_configs WHERE id = ?", (config_id,))
    return cur.rowcount > 0


# ---------- Workflow ----------

def list_workflows() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT name, updated_at FROM workflows ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_workflow(name: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM workflows WHERE name = ?", (name,)).fetchone()
    return json.loads(row["data"]) if row else None


def save_workflow(name: str, data: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO workflows (name, data) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET data=excluded.data, "
            "updated_at=datetime('now', 'localtime')",
            (name, json.dumps(data, ensure_ascii=False)))


def delete_workflow(name: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM workflows WHERE name = ?", (name,))
    return cur.rowcount > 0


def workflow_exists(name: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM workflows WHERE name = ?", (name,)).fetchone()
    return row is not None


# ---------- Lịch sử thực thi (exec history) ----------

EXEC_RETENTION = 50  # mỗi workflow giữ tối đa N bản ghi gần nhất; prune sau khi chốt


def create_execution(name: str, mode: str) -> int:
    """Tạo bản ghi exec trạng thái 'running'; trả id để cập nhật khi chạy xong."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO workflow_executions (workflow_name, mode, status) "
            "VALUES (?, ?, 'running')",
            (name, mode))
        return cur.lastrowid


def finish_execution(exec_id: int, status: str, error: str, detail: dict,
                     duration_ms: int | None) -> None:
    """Chốt bản ghi exec (status/error/detail/duration) rồi prune giữ top-50/workflow."""
    with _connect() as conn:
        conn.execute(
            "UPDATE workflow_executions SET status=?, error=?, detail=?, "
            "duration_ms=?, finished_at=datetime('now','localtime') WHERE id=?",
            (status, error, json.dumps(detail, ensure_ascii=False), duration_ms, exec_id))
        row = conn.execute(
            "SELECT workflow_name FROM workflow_executions WHERE id=?",
            (exec_id,)).fetchone()
        if row:
            # Xóa bản ghi cũ hơn top-EXEC_RETENTION cùng workflow (id lớn = mới hơn).
            conn.execute(
                "DELETE FROM workflow_executions WHERE workflow_name=? AND id NOT IN ("
                "  SELECT id FROM workflow_executions WHERE workflow_name=? "
                "  ORDER BY id DESC LIMIT ?)",
                (row["workflow_name"], row["workflow_name"], EXEC_RETENTION))


def list_executions(name: str, limit: int, offset: int) -> tuple[list[dict], int]:
    """Trả (rows, total) bản ghi exec của workflow, mới nhất trước, có paging."""
    with _connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM workflow_executions WHERE workflow_name=?",
            (name,)).fetchone()["c"]
        rows = conn.execute(
            "SELECT id, workflow_name, mode, status, error, started_at, "
            "finished_at, duration_ms FROM workflow_executions "
            "WHERE workflow_name=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (name, limit, offset)).fetchall()
    return [dict(r) for r in rows], total


def get_execution(exec_id: int) -> dict | None:
    """Bản ghi exec đầy đủ; `detail` parse sẵn thành dict."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM workflow_executions WHERE id=?", (exec_id,)).fetchone()
    if not row:
        return None
    rec = dict(row)
    try:
        rec["detail"] = json.loads(rec.get("detail") or "{}")
    except json.JSONDecodeError:
        rec["detail"] = {}
    return rec


def delete_execution(exec_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM workflow_executions WHERE id=?", (exec_id,))
    return cur.rowcount > 0


def clear_executions(name: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM workflow_executions WHERE workflow_name=?", (name,))
    return cur.rowcount
