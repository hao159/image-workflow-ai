"""Test engine harness critic-refine loop (opt-in).

Bất biến cần khóa:
  - harness=None → chạy 1 pass như cũ (backward compat, KHÔNG có event harness_*).
  - Dừng khi critic passed; dừng khi hết max_iterations.
  - Xuất iteration ĐIỂM CAO NHẤT (best≠last) — ảnh best là cái được lưu.
  - Feedback APPEND vào prompt node sinh, tích lũy qua các vòng.
  - Goal = prompt đã merge (kể cả prompt từ cổng nối).
  - Critic không vision → run_error TRƯỚC khi sinh (không tốn lượt).
  - Node lỗi giữa loop → giữ best + harness_report (stopped_early), không mất best.
  - 0 node sinh / nhiều sink → run_error rõ.

Test thuần Python — KHÔNG cần server/token. Stub provider qua monkeypatch:
  - generate node: app.nodes.generate.resolve_model_config
  - critic:        app.engine.resolve_model_config

Chạy: backend\\.venv\\Scripts\\python.exe test_harness_loop.py
"""
import asyncio
import tempfile
from pathlib import Path

from app import cache, config
from app import engine as engine_module
from app.engine import run_workflow
from app.models import EdgeDef, HarnessConfig, NodeDef, Workflow
from app.nodes import generate as generate_module

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415408d763f8cfc0f01f0005010100a5e3a4f70000000049454e44ae426082")


class GenStub:
    """Sinh ảnh có MARKER theo số lần gọi → phân biệt ảnh iteration nào được lưu."""

    def __init__(self):
        self.calls = 0
        self.prompts = []

    def generate(self, prompt, **kw):
        self.prompts.append(prompt)
        out = _PNG + b"::" + str(self.calls).encode()
        self.calls += 1
        return out


class FailingGen(GenStub):
    def __init__(self, fail_on):
        super().__init__()
        self.fail_on = fail_on

    def generate(self, prompt, **kw):
        if self.calls >= self.fail_on:
            self.calls += 1
            raise RuntimeError("boom")
        return super().generate(prompt, **kw)


class ScriptedCritic:
    """Critic chấm theo kịch bản điểm; ghi goal nhận được để kiểm."""

    def __init__(self, scores):
        self.scores = scores
        self.calls = 0
        self.goals = []

    @classmethod
    def supports_critique(cls):
        return True

    def critique_image(self, image, goal, criteria="", *, model="", **kw):
        self.goals.append(goal)
        i = self.calls
        self.calls += 1
        score = self.scores[min(i, len(self.scores) - 1)]
        return {"score": score, "passed": False, "feedback": f"fix{i}"}


class NoVisionCritic:
    @classmethod
    def supports_critique(cls):
        return False


def _gen(nid, prompt):
    return NodeDef(id=nid, type="generate_image",
                   params={"provider": "cfg", "prompt": prompt})


def _save(nid):
    return NodeDef(id=nid, type="save_image", params={"prefix": "t"})


def _text(nid, text):
    return NodeDef(id=nid, type="text_prompt", params={"text": text})


def _edge(src, tgt, handle, src_handle="image"):
    return EdgeDef(source=src, sourceHandle=src_handle, target=tgt, targetHandle=handle)


def _run(workflow, gen_stub, critic, *, max_iterations=3, pass_score=8.0,
         criteria="", harness_enabled=True):
    """Patch provider + critic, chạy workflow harness, khôi phục. Trả events."""
    gen_orig = generate_module.resolve_model_config
    eng_orig = engine_module.resolve_model_config
    generate_module.resolve_model_config = lambda sel: (gen_stub, "")
    engine_module.resolve_model_config = lambda sel: (critic, "")
    events = []

    async def emit(ev):
        events.append(ev)

    cache_orig = cache.CACHE_DIR
    out_orig = config.OUTPUTS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        cache.CACHE_DIR = Path(tmp) / "cache"
        cache.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        config.OUTPUTS_DIR = Path(tmp) / "out"
        config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        harness = HarnessConfig(enabled=harness_enabled, max_iterations=max_iterations,
                                pass_score=pass_score, criteria=criteria,
                                critic_provider="critic-cfg")
        try:
            asyncio.run(run_workflow(workflow, emit, harness=harness))
            saved = sorted(config.OUTPUTS_DIR.glob("*.png"))
            saved_bytes = [p.read_bytes() for p in saved]
        finally:
            generate_module.resolve_model_config = gen_orig
            engine_module.resolve_model_config = eng_orig
            cache.CACHE_DIR = cache_orig
            config.OUTPUTS_DIR = out_orig
    return events, saved_bytes


def _types(events):
    return [e.type for e in events]


# ---------- backward compat ----------

def test_harness_none_runs_single_pass():
    # harness=None → 1 pass, KHÔNG event harness_*, không lỗi
    gen = GenStub()
    gen_orig = generate_module.resolve_model_config
    generate_module.resolve_model_config = lambda sel: (gen, "")
    events = []

    async def emit(ev):
        events.append(ev)

    cache_orig = cache.CACHE_DIR
    out_orig = config.OUTPUTS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        cache.CACHE_DIR = Path(tmp) / "c"
        cache.CACHE_DIR.mkdir(parents=True)
        config.OUTPUTS_DIR = Path(tmp) / "o"
        config.OUTPUTS_DIR.mkdir(parents=True)
        wf = Workflow(nodes=[_gen("g", "mèo"), _save("s")],
                      edges=[_edge("g", "s", "image")])
        try:
            asyncio.run(run_workflow(wf, emit, harness=None))
        finally:
            generate_module.resolve_model_config = gen_orig
            cache.CACHE_DIR = cache_orig
            config.OUTPUTS_DIR = out_orig
    ts = _types(events)
    assert "harness_iteration" not in ts and "harness_report" not in ts, ts
    assert ts[0] == "run_started" and ts[-1] == "run_finished", ts
    assert gen.calls == 1


# ---------- dừng khi đạt / hết limit ----------

def test_stops_when_passed_first_iteration():
    gen, critic = GenStub(), ScriptedCritic([9.0])
    events, saved = _run(Workflow(nodes=[_gen("g", "mèo"), _save("s")],
                                  edges=[_edge("g", "s", "image")]),
                         gen, critic, pass_score=8.0)
    ts = _types(events)
    assert ts.count("harness_iteration") == 1, ts
    assert "harness_report" in ts and ts[-1] == "run_finished", ts
    assert gen.calls == 1, gen.calls
    report = next(e for e in events if e.type == "harness_report")
    assert report.report["best_iteration"] == 0
    assert len(saved) == 1  # sink chạy đúng 1 lần


def test_stops_at_max_iterations():
    gen, critic = GenStub(), ScriptedCritic([5.0, 6.0, 7.0])
    events, saved = _run(Workflow(nodes=[_gen("g", "mèo"), _save("s")],
                                  edges=[_edge("g", "s", "image")]),
                         gen, critic, max_iterations=3, pass_score=8.0)
    ts = _types(events)
    assert ts.count("harness_iteration") == 3, ts
    assert gen.calls == 3, gen.calls
    report = next(e for e in events if e.type == "harness_report")
    assert report.report["best_iteration"] == 2  # điểm 7 cao nhất = iter cuối
    assert len(saved) == 1


# ---------- best ≠ last ----------

def test_best_not_last_saves_best_image():
    gen, critic = GenStub(), ScriptedCritic([6.0, 9.0, 4.0])
    events, saved = _run(Workflow(nodes=[_gen("g", "mèo"), _save("s")],
                                  edges=[_edge("g", "s", "image")]),
                         gen, critic, max_iterations=3, pass_score=10.0)
    report = next(e for e in events if e.type == "harness_report")
    assert report.report["best_iteration"] == 1, report.report
    assert report.report["best_score"] == 9.0
    # Ảnh lưu = ảnh iteration 1 (marker "::1"), KHÔNG phải iter cuối "::2"
    assert len(saved) == 1, saved
    assert saved[0].endswith(b"::1"), saved[0][-6:]


# ---------- feedback append + accumulate ----------

def test_feedback_appended_and_accumulated():
    gen, critic = GenStub(), ScriptedCritic([5.0, 6.0, 7.0])
    _run(Workflow(nodes=[_gen("g", "mèo"), _save("s")],
                  edges=[_edge("g", "s", "image")]),
         gen, critic, max_iterations=3, pass_score=8.0)
    # iter0 prompt = "mèo" (chưa feedback); iter1 chứa fix0; iter2 chứa fix0+fix1
    assert "Phản hồi chỉnh sửa" not in gen.prompts[0], gen.prompts[0]
    assert "fix0" in gen.prompts[1], gen.prompts[1]
    assert "fix0" in gen.prompts[2] and "fix1" in gen.prompts[2], gen.prompts[2]
    # prompt gốc vẫn còn
    assert "mèo" in gen.prompts[2]


# ---------- goal từ cổng nối ----------

def test_goal_from_connected_prompt_port():
    gen, critic = GenStub(), ScriptedCritic([9.0])
    wf = Workflow(
        nodes=[_text("t", "vẽ mèo rồng"), _gen("g", ""), _save("s")],
        edges=[_edge("t", "g", "prompt", src_handle="text"),
               _edge("g", "s", "image")])
    _run(wf, gen, critic, pass_score=8.0)
    # Goal critic nhận = prompt đã merge từ cổng (không phải param rỗng)
    assert critic.goals[0] == "vẽ mèo rồng", critic.goals


# ---------- critic không vision → lỗi trước khi sinh ----------

def test_non_vision_critic_errors_before_generating():
    gen = GenStub()
    events, _ = _run(Workflow(nodes=[_gen("g", "mèo"), _save("s")],
                              edges=[_edge("g", "s", "image")]),
                     gen, NoVisionCritic(), pass_score=8.0)
    ts = _types(events)
    assert "run_error" in ts, ts
    assert gen.calls == 0, "không được sinh ảnh khi critic không chấm được"
    err = next(e for e in events if e.type == "run_error")
    assert "vision" in err.message or "Gemini" in err.message


# ---------- node lỗi giữa loop → giữ best ----------

def test_node_failure_midloop_keeps_best():
    gen, critic = FailingGen(fail_on=1), ScriptedCritic([6.0])  # iter0 ok, iter1 raise
    events, saved = _run(Workflow(nodes=[_gen("g", "mèo"), _save("s")],
                                  edges=[_edge("g", "s", "image")]),
                         gen, critic, max_iterations=3, pass_score=10.0)
    ts = _types(events)
    report = next((e for e in events if e.type == "harness_report"), None)
    assert report is not None and report.report.get("stopped_early"), ts
    assert report.report["best_iteration"] == 0
    assert ts[-1] == "run_finished", ts  # không giết bằng run_error khi đã có best
    assert len(saved) == 1  # vẫn lưu được best


# ---------- locate errors ----------

def test_no_generative_node_errors():
    gen, critic = GenStub(), ScriptedCritic([9.0])
    # load_image → save: không có node Tạo/Sửa → lỗi (không chạy node)
    wf = Workflow(nodes=[NodeDef(id="l", type="load_image", params={}), _save("s")],
                  edges=[_edge("l", "s", "image")])
    events, _ = _run(wf, gen, critic)
    ts = _types(events)
    assert "run_error" in ts, ts
    assert gen.calls == 0


def test_multiple_sinks_error():
    gen, critic = GenStub(), ScriptedCritic([9.0])
    wf = Workflow(nodes=[_gen("g", "mèo"), _save("s1"), _save("s2")],
                  edges=[_edge("g", "s1", "image"), _edge("g", "s2", "image")])
    events, _ = _run(wf, gen, critic)
    ts = _types(events)
    assert "run_error" in ts, ts


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL  {fn.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    raise SystemExit(0 if passed == len(tests) else 1)
