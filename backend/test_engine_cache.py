"""Test cache memoization của engine (Phase 1) — offline, không cần backend/token.

Chứng minh cache-hit KHÔNG thực thi lại node bằng cách đếm số lần `run` được gọi
(`_CountNode.calls`). Cũng kiểm target-prune, force, persistence, clear, eviction.

Chạy: backend\\.venv\\Scripts\\python.exe test_engine_cache.py
"""
import asyncio
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from app import cache
from app.engine import run_workflow
from app.models import Workflow
from app.nodes.base import BaseNode, NODE_REGISTRY, Param, Port

# Cache ghi vào thư mục tạm — không đụng cache thật của project.
cache.CACHE_DIR = Path(tempfile.mkdtemp(prefix="wfcache_test_"))
_DEFAULT_MAX = cache.CACHE_MAX_BYTES


class _CountNode(BaseNode):
    """Node test: đếm số lần chạy theo param `id`. Param `v` để đổi → vô hiệu key."""
    type_name = "_count"
    title = "Count"
    category = "Test"
    inputs = [Port("in", "text", "In", required=False)]
    outputs = [Port("out", "text", "Out")]
    params = [Param("id", "text", "Id", default=""), Param("v", "text", "V", default="")]
    calls: dict = defaultdict(int)

    def run(self, inputs, params):
        _CountNode.calls[params.get("id", "")] += 1
        return {"out": params.get("id", "")}


def _node(nid, **params):
    return {"id": nid, "type": "_count", "params": params}


def _edge(src, tgt):
    return {"source": src, "sourceHandle": "out", "target": tgt, "targetHandle": "in"}


def _wf(nodes, edges):
    return Workflow.model_validate({"name": "t", "nodes": nodes, "edges": edges})


def _run(wf, **kw):
    events = []

    async def emit(ev):
        events.append(ev)

    asyncio.run(run_workflow(wf, emit, **kw))
    return events


def _reset():
    cache.CACHE_MAX_BYTES = _DEFAULT_MAX
    cache.clear()
    _CountNode.calls = defaultdict(int)


# ---------- cache hit / invalidation ----------

def test_hit_second_run():
    _reset()
    wf = _wf([_node("a", id="a"), _node("b", id="b")], [_edge("a", "b")])
    _run(wf)
    assert _CountNode.calls["a"] == 1 and _CountNode.calls["b"] == 1
    events = _run(wf)  # y hệt → cache-hit cả hai
    assert _CountNode.calls["a"] == 1 and _CountNode.calls["b"] == 1
    finished = [e for e in events if e.type == "node_finished"]
    assert all(e.cached for e in finished), "lần 2 phải toàn cache-hit"


def test_param_change_reruns_self_and_downstream():
    _reset()
    _run(_wf([_node("a", id="a"), _node("b", id="b")], [_edge("a", "b")]))
    # đổi param `v` của b → key b đổi, a giữ nguyên
    _run(_wf([_node("a", id="a"), _node("b", id="b", v="x")], [_edge("a", "b")]))
    assert _CountNode.calls["a"] == 1, "a không đổi → cache-hit"
    assert _CountNode.calls["b"] == 2, "b đổi param → chạy lại"


def test_upstream_change_invalidates_downstream():
    _reset()
    _run(_wf([_node("a", id="a"), _node("b", id="b")], [_edge("a", "b")]))
    # đổi param a → key a đổi → out_key a đổi → key b đổi (Merkle) → cả hai chạy lại
    _run(_wf([_node("a", id="a", v="x"), _node("b", id="b")], [_edge("a", "b")]))
    assert _CountNode.calls["a"] == 2 and _CountNode.calls["b"] == 2


def test_unrelated_branch_cached():
    _reset()
    nodes = [_node("a1", id="a1"), _node("a2", id="a2"),
             _node("b1", id="b1"), _node("b2", id="b2")]
    edges = [_edge("a1", "a2"), _edge("b1", "b2")]
    _run(_wf(nodes, edges))
    # đổi nhánh a → chỉ a1/a2 chạy lại; nhánh b giữ cache
    nodes2 = [_node("a1", id="a1", v="x"), _node("a2", id="a2"),
              _node("b1", id="b1"), _node("b2", id="b2")]
    _run(_wf(nodes2, edges))
    assert _CountNode.calls["a1"] == 2 and _CountNode.calls["a2"] == 2
    assert _CountNode.calls["b1"] == 1 and _CountNode.calls["b2"] == 1


# ---------- target / force ----------

def test_target_prune():
    _reset()
    nodes = [_node("a", id="a"), _node("b", id="b"), _node("c", id="c")]
    edges = [_edge("a", "b"), _edge("b", "c")]
    _run(_wf(nodes, edges), target="b")
    assert _CountNode.calls["a"] == 1 and _CountNode.calls["b"] == 1
    assert _CountNode.calls["c"] == 0, "target=b → c không được chạy"


def test_force_reruns_target_only():
    _reset()
    wf = _wf([_node("a", id="a"), _node("b", id="b")], [_edge("a", "b")])
    _run(wf)  # cache a,b
    _run(wf, target="b", force_ids=frozenset({"b"}))
    assert _CountNode.calls["a"] == 1, "a cache-hit (upstream)"
    assert _CountNode.calls["b"] == 2, "b bị ép chạy lại"


# ---------- persistence / clear ----------

def test_disk_persistence():
    _reset()
    _run(_wf([_node("a", id="a"), _node("b", id="b")], [_edge("a", "b")]))
    manifests = list((cache.CACHE_DIR / "nodes").glob("*.json"))
    assert len(manifests) >= 2, "cache phải ghi manifest ra đĩa"


def test_clear():
    _reset()
    wf = _wf([_node("a", id="a")], [])
    _run(wf)
    cache.clear()
    _run(wf)
    assert _CountNode.calls["a"] == 2, "sau clear → chạy lại"


# ---------- auto-trim (eviction) ----------

def test_evict_over_limit():
    _reset()
    blobs = cache.CACHE_DIR / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    shas = []
    for i in range(5):
        data = bytes([i]) * 400  # 5 blob × 400B = 2000B
        sha = hashlib.sha256(data).hexdigest()
        (blobs / f"{sha}.bin").write_bytes(data)
        shas.append(sha)
    # mtime tăng dần theo i → shas[0] cũ nhất
    for i, sha in enumerate(shas):
        os.utime(blobs / f"{sha}.bin", (1_000_000 + i, 1_000_000 + i))

    cache.CACHE_MAX_BYTES = 1000
    cache._evict_if_needed()
    total = sum(p.stat().st_size for p in blobs.glob("*.bin"))
    assert total <= 1000, f"tổng blobs {total} phải <= 1000"
    assert not (blobs / f"{shas[0]}.bin").exists(), "blob cũ nhất phải bị xóa"
    assert (blobs / f"{shas[4]}.bin").exists(), "blob mới nhất phải còn"

    # manifest mồ côi (trỏ blob đã evict) → load trả None (miss an toàn)
    (cache.CACHE_DIR / "nodes" / "orphan.json").write_text(
        json.dumps({"outputs": {"image": {"dtype": "image", "blob": shas[0]}},
                    "preview": None}), encoding="utf-8")
    assert cache.load("orphan") is None


if __name__ == "__main__":
    NODE_REGISTRY["_count"] = _CountNode
    try:
        tests = [v for k, v in sorted(globals().items())
                 if k.startswith("test_") and callable(v)]
        passed = 0
        for fn in tests:
            try:
                fn()
                print(f"  PASS  {fn.__name__}")
                passed += 1
            except Exception as e:  # noqa: BLE001
                import traceback
                print(f"  FAIL  {fn.__name__}: {e}")
                traceback.print_exc()
        print(f"\n{passed}/{len(tests)} tests passed")
    finally:
        NODE_REGISTRY.pop("_count", None)
    raise SystemExit(0 if passed == len(tests) else 1)
