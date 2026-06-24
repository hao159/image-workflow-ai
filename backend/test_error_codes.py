"""Test: every user-facing backend error response carries a stable `code` slug.

Run: backend\\.venv\\Scripts\\python.exe -m pytest test_error_codes.py -v
(run from backend/ directory, or pass full path)
"""
import sys
import os

# Ensure 'backend/' is on sys.path so `from app.xxx import ...` works (same
# convention as all other backend test files in this directory).
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------- model-config HTTP errors ----------

def test_model_config_empty_name_has_code():
    r = client.post("/api/model-configs", json={"name": "", "provider": "gemini"})
    assert r.status_code == 400
    body = r.json()
    assert body.get("code") == "config_name_empty"
    assert body.get("error")  # Vietnamese message preserved


def test_model_config_invalid_provider_has_code():
    r = client.post("/api/model-configs", json={"name": "x", "provider": "unknown_xyz"})
    assert r.status_code == 400
    body = r.json()
    assert body.get("code") == "config_provider_invalid"
    assert body.get("error")


def test_model_config_not_found_has_code():
    r = client.delete("/api/model-configs/999999")
    assert r.status_code == 404
    assert r.json().get("code") == "config_not_found"


# ---------- workflow HTTP errors ----------

def test_workflow_not_found_has_code():
    r = client.get("/api/workflows/__definitely_missing__")
    assert r.status_code == 404
    assert r.json().get("code") == "workflow_not_found"


def test_workflow_delete_not_found_has_code():
    r = client.delete("/api/workflows/__definitely_missing__")
    assert r.status_code == 404
    assert r.json().get("code") == "workflow_not_found"


def test_workflow_exists_has_code():
    """409 conflict keeps 'exists'/'name' keys AND adds code."""
    # Create a workflow first
    client.post("/api/workflows", json={"name": "dup_test_wf", "nodes": [], "edges": []})
    r = client.post("/api/workflows",
                    json={"name": "dup_test_wf", "nodes": [], "edges": []})
    assert r.status_code == 409
    body = r.json()
    assert body.get("code") == "workflow_exists"
    assert body.get("error") == "exists"  # original key preserved
    assert body.get("name") == "dup_test_wf"
    # cleanup
    client.delete("/api/workflows/dup_test_wf")


# ---------- upload HTTP errors ----------

def test_upload_unsupported_format_has_code():
    r = client.post("/api/upload", files={"file": ("bad.txt", b"hello", "text/plain")})
    assert r.status_code == 400
    assert r.json().get("code") == "upload_format_unsupported"


# ---------- file not found ----------

def test_upload_file_not_found_has_code():
    r = client.get("/api/uploads/__no_such_file__.png")
    assert r.status_code == 404
    assert r.json().get("code") == "file_not_found"


def test_output_file_not_found_has_code():
    r = client.get("/api/outputs/__no_such_file__.png")
    assert r.status_code == 404
    assert r.json().get("code") == "file_not_found"


# ---------- execution not found ----------

def test_execution_not_found_has_code():
    r = client.get("/api/executions/999999999")
    assert r.status_code == 404
    assert r.json().get("code") == "execution_not_found"


# ---------- RunEvent model has code + params fields ----------

def test_run_event_model_has_code_field():
    from app.models import RunEvent
    ev = RunEvent(type="node_error", message="oops", code="generate_no_prompt")
    assert ev.code == "generate_no_prompt"
    assert ev.params is None


def test_run_event_model_has_params_field():
    from app.models import RunEvent
    ev = RunEvent(type="node_error", message="x", code="load_image_missing",
                  params={"node": "n1"})
    assert ev.params == {"node": "n1"}


# ---------- NodeInputError carries code ----------

def test_node_input_error_carries_code():
    from app.nodes._errors import NodeInputError
    e = NodeInputError("msg", "generate_no_prompt")
    assert e.code == "generate_no_prompt"
    assert e.params == {}
    assert isinstance(e, ValueError)


def test_node_input_error_carries_params():
    from app.nodes._errors import NodeInputError
    e = NodeInputError("msg", "load_image_missing", {"file_id": "x"})
    assert e.params == {"file_id": "x"}
