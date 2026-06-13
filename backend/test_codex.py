"""Unit test cho Codex OAuth + provider (không cần token thật / server chạy).

Chạy: backend\\.venv\\Scripts\\python.exe -m pytest test_codex.py  (nếu có pytest)
Hoặc:  backend\\.venv\\Scripts\\python.exe test_codex.py            (chạy thẳng)
"""
import base64

from app.nodes import node_type_metadata
from app.providers import PROVIDER_NAMES, make_provider, provider_options
from app.providers import openai_codex_oauth as oauth
from app.providers.openai_codex import OpenAICodexProvider, _parse_image_from_sse

# PNG 1x1 hợp lệ (đỏ) để test parser
_PNG_1X1 = base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415408d763f8cfc0f01f0005010100a5e3a4f70000000049454e44ae426082"
)).decode()
_PNG_MAGIC = bytes.fromhex("89504e470d0a1a0a")


def test_pkce_format():
    verifier, challenge = oauth.generate_pkce()
    assert len(verifier) >= 43
    assert "=" not in challenge  # base64url không padding
    assert "+" not in challenge and "/" not in challenge


def test_authorize_url_params():
    _, challenge = oauth.generate_pkce()
    url = oauth.build_authorize_url(challenge, "state123")
    for needle in ("client_id=app_EMoamEEZ", "code_challenge_method=S256",
                   "state=state123", "redirect_uri=http", "originator=codex_cli_rs"):
        assert needle in url, f"thiếu {needle} trong authorize url"


def test_decode_jwt_payload():
    # JWT giả: header.payload.sig với payload = {"foo":"bar"}
    payload = base64.urlsafe_b64encode(b'{"foo":"bar"}').rstrip(b"=").decode()
    token = f"x.{payload}.y"
    assert oauth._decode_jwt_payload(token).get("foo") == "bar"
    assert oauth._decode_jwt_payload("rác").get("foo") is None  # không crash


def test_account_id_from_id_token():
    claims = '{"https://api.openai.com/auth":{"chatgpt_account_id":"acc-xyz"}}'
    payload = base64.urlsafe_b64encode(claims.encode()).rstrip(b"=").decode()
    assert oauth._account_id_from_id_token(f"x.{payload}.y") == "acc-xyz"


def test_sse_parser_done_event():
    lines = [
        'data: {"type":"response.image_generation_call.in_progress"}',
        'data: {"type":"response.image_generation_call.generating"}',
        'data: {"type":"response.output_item.done","item":{"type":"image_generation_call","result":"' + _PNG_1X1 + '"}}',
        "data: [DONE]",
    ]
    out = _parse_image_from_sse(iter(lines))
    assert out[:8] == _PNG_MAGIC


def test_sse_parser_completed_fallback():
    line = 'data: {"type":"response.completed","response":{"output":[{"type":"image_generation_call","result":"' + _PNG_1X1 + '"}]}}'
    assert _parse_image_from_sse(iter([line]))[:8] == _PNG_MAGIC


def test_sse_parser_partial_only_raises():
    # partial_image là preview dở dang — KHÔNG được trả làm kết quả; stream chỉ
    # có partial (đứt giữa chừng) phải raise lỗi rõ thay vì trả ảnh mờ.
    lines = [
        'data: {"type":"response.image_generation_call.partial_image","partial_image_b64":"' + _PNG_1X1 + '"}',
        "data: [DONE]",
    ]
    try:
        _parse_image_from_sse(iter(lines))
    except Exception:
        pass
    else:
        raise AssertionError("partial-only stream phải raise")


def test_sse_parser_error_raises():
    try:
        _parse_image_from_sse(iter(['data: {"type":"response.failed","response":{"error":"quota"}}']))
    except Exception as e:
        assert "quota" in str(e)
    else:
        raise AssertionError("phải raise khi gặp response.failed")


def test_sse_parser_deadline_raises():
    # deadline_s=-1 → hết hạn ngay dòng đầu (mô phỏng stream chạy quá lâu)
    lines = ['data: {"type":"response.image_generation_call.generating"}'] * 5
    try:
        _parse_image_from_sse(iter(lines), deadline_s=-1)
    except Exception as e:
        assert "quá" in str(e)
    else:
        raise AssertionError("phải raise khi vượt deadline")


def test_debug_log_noop_when_disabled():
    # Ép CODEX_DEBUG=False (môi trường thật có thể đang bật trong .env) →
    # mọi method phải no-op, tee trả nguyên iterator
    from app.providers import codex_debug_log as cdl
    orig = cdl.CODEX_DEBUG
    cdl.CODEX_DEBUG = False
    try:
        log = cdl.CodexDebugLog()
        assert log.path is None
        log.request("http://x", {"input": []})
        log.done("ok")
        log.close()
        assert list(log.tee(iter(["a", "b"]))) == ["a", "b"]
    finally:
        cdl.CODEX_DEBUG = orig


def test_sse_parser_no_image_raises():
    try:
        _parse_image_from_sse(iter(['data: {"type":"response.completed","response":{"output":[]}}']))
    except Exception:
        pass
    else:
        raise AssertionError("phải raise khi stream không có ảnh")


def test_provider_options_no_raw_providers():
    # Dropdown node chỉ chứa config đặt tên, không còn provider thô
    opts = provider_options()
    for raw in ("gemini", "openai", "codex", "comfyui"):
        assert raw not in opts, f"provider thô '{raw}' lọt vào dropdown"


def test_make_provider_codex_no_api_key():
    assert "codex" in PROVIDER_NAMES
    p = make_provider("codex")
    assert isinstance(p, OpenAICodexProvider)


def test_nodes_have_no_model_param():
    meta = {m["type"]: m for m in node_type_metadata()}
    for t in ("generate_image", "edit_image"):
        params = meta[t]["params"]
        assert not any(p["name"] == "model" for p in params), f"{t} vẫn còn param model"
        provider = next(p for p in params if p["name"] == "provider")
        assert "options" in provider, f"{t} provider param thiếu key options (frontend sẽ vỡ)"


def test_sse_text_parser_message_done():
    from app.providers.codex_sse_parsers import _parse_text_from_sse
    lines = [
        'data: {"type":"response.output_item.done","item":{"type":"reasoning","content":[]}}',
        'data: {"type":"response.output_item.done","item":{"type":"message","content":[{"type":"output_text","text":"a red fox, "},{"type":"output_text","text":"golden hour"}]}}',
        "data: [DONE]",
    ]
    assert _parse_text_from_sse(iter(lines)) == "a red fox, golden hour"


def test_sse_text_parser_completed_fallback_and_errors():
    from app.providers.codex_sse_parsers import _parse_text_from_sse
    line = 'data: {"type":"response.completed","response":{"output":[{"type":"message","content":[{"type":"output_text","text":"ok"}]}]}}'
    assert _parse_text_from_sse(iter([line])) == "ok"
    for bad in ('data: {"type":"response.failed","response":{"error":"quota"}}',
                'data: {"type":"response.completed","response":{"output":[]}}'):
        try:
            _parse_text_from_sse(iter([bad]))
        except Exception:
            pass
        else:
            raise AssertionError(f"phải raise với stream: {bad}")


def test_enhance_prompt_node():
    # Node gọi provider.generate_text với system instruction chứa số từ mục tiêu
    from app.nodes.enhance_prompt import EnhancePromptNode
    from app.nodes import enhance_prompt as ep_module

    meta = {m["type"]: m for m in node_type_metadata()}
    assert "enhance_prompt" in meta, "node enhance_prompt chưa đăng ký"
    assert "options" in next(p for p in meta["enhance_prompt"]["params"]
                             if p["name"] == "provider")

    calls = {}

    class FakeProvider:
        def generate_text(self, prompt, *, model="", system="", **_):
            calls.update(prompt=prompt, model=model, system=system)
            return "enhanced!"

    orig = ep_module.resolve_model_config
    ep_module.resolve_model_config = lambda sel: (FakeProvider(), "m1")
    try:
        out = EnhancePromptNode().run(
            {"text": "con cáo"}, {"provider": "cfg", "style": "phong cách anime",
                                  "detail": "dài", "prompt": ""})
    finally:
        ep_module.resolve_model_config = orig
    assert out == {"text": "enhanced!"}
    assert calls["prompt"] == "con cáo" and calls["model"] == "m1"
    assert "150" in calls["system"] and "anime" in calls["system"]

    # Thiếu prompt → lỗi rõ
    try:
        EnhancePromptNode().run({}, {"provider": "cfg", "prompt": "", "style": "",
                                     "detail": "vừa"})
    except ValueError:
        pass
    else:
        raise AssertionError("thiếu prompt phải raise ValueError")


def test_comfyui_generate_text_raises():
    # Provider không có LLM text phải báo lỗi rõ, không crash khó hiểu
    p = make_provider("comfyui")
    try:
        p.generate_text("x")
    except Exception as e:
        assert "không hỗ trợ sinh text" in str(e)
    else:
        raise AssertionError("comfyui generate_text phải raise")


def test_oauth_status_shape():
    st = oauth.status()
    assert "logged_in" in st
    if st["logged_in"]:
        assert "account_id" in st and "expired" in st


def test_numbered_image_caption():
    from app.providers.base import numbered_image_caption
    assert numbered_image_caption(0, "khung") == "Ảnh 1: khung"
    assert numbered_image_caption(3, "") == "Ảnh 4: (không mô tả)"
    assert numbered_image_caption(1, "  Tiến  ") == "Ảnh 2: Tiến"


def test_codex_edit_interleaves_image_labels():
    # edit() xen caption "Ảnh N: <tên>" NGAY TRƯỚC mỗi input_image
    p = OpenAICodexProvider()
    cap = {}
    p._request_image = lambda model, content, **kw: cap.update(content=content) or b"OUT"
    out = p.edit([b"img0", b"img1"], "prompt chính", image_labels=["khung", "Tiến"])
    c = cap["content"]
    assert c[0] == {"type": "input_text", "text": "prompt chính"}
    assert c[1] == {"type": "input_text", "text": "Ảnh 1: khung"}
    assert c[2]["type"] == "input_image"
    assert c[3] == {"type": "input_text", "text": "Ảnh 2: Tiến"}
    assert c[4]["type"] == "input_image"
    assert out == b"OUT"


def test_codex_edit_no_labels_bare_images():
    # Không nhãn → ảnh trần, không caption (backward compat)
    p = OpenAICodexProvider()
    cap = {}
    p._request_image = lambda model, content, **kw: cap.update(content=content) or b"OUT"
    p.edit([b"img0"], "prompt", image_labels=None)
    c = cap["content"]
    assert c[0]["type"] == "input_text" and c[1]["type"] == "input_image"
    assert len(c) == 2  # chỉ prompt + 1 ảnh, không caption


def test_gemini_edit_interleaves_image_labels():
    # Gemini xen caption (str) ngay trước Part ảnh trong contents
    from app.providers.gemini import GeminiProvider

    class _Inline:
        data = _PNG_MAGIC

    class _Part:
        inline_data = _Inline()

    class _Resp:
        parts = [_Part()]

    class _Models:
        def generate_content(self, *, model, contents, config):
            _Models.captured = contents
            return _Resp()

    class _Client:
        models = _Models()

    p = GeminiProvider(api_key="x")
    p._client = _Client()
    out = p.edit([b"a", b"b"], "prompt chính", image_labels=["khung", "Tiến"])
    c = _Models.captured
    assert c[0] == "prompt chính"
    assert c[1] == "Ảnh 1: khung"
    assert c[3] == "Ảnh 2: Tiến"
    assert out == _PNG_MAGIC


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
