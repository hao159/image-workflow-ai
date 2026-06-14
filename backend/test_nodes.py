"""Test logic ghép prompt (merge_prompt) và node Ghép prompt (combine_text).

Test thuần Python — không cần backend chạy, không cần API token.

Chạy: backend\\.venv\\Scripts\\python.exe -m pytest test_nodes.py  (nếu có pytest)
Hoặc:  backend\\.venv\\Scripts\\python.exe test_nodes.py            (chạy thẳng)
"""
from app.nodes.edit import EditImageNode
from app.nodes.generate import GenerateImageNode
from app.nodes.image_label_block import (IMAGE_REF_INSTRUCTION,
                                         build_reference_block, compose_edit_prompt)
from app.nodes.inputs import CombineTextNode, LoadImageNode
from app.nodes.prompt_merge import merge_prompt


# ---------- merge_prompt: ghép prompt nối + prompt bổ sung ----------

def test_merge_both():
    assert merge_prompt("mèo", "sơn dầu") == "mèo, sơn dầu"


def test_merge_connected_only():
    assert merge_prompt("mèo", "") == "mèo"


def test_merge_supplement_only():
    # Không nối (connected=None) → dùng prompt gõ trực tiếp, giữ hành vi cũ
    assert merge_prompt(None, "mèo") == "mèo"


def test_merge_empty():
    assert merge_prompt("", None) == ""


def test_merge_strips_whitespace():
    assert merge_prompt("  mèo  ", "  sơn dầu  ") == "mèo, sơn dầu"


# ---------- CombineTextNode: ghép nhiều prompt bằng xuống dòng ----------

def test_combine_multi_order():
    out = CombineTextNode().run({"texts": ["a", "b", "c"]}, {})
    assert out["text"] == "a\nb\nc"


def test_combine_filters_empty():
    out = CombineTextNode().run({"texts": ["a", "  ", "", "b"]}, {})
    assert out["text"] == "a\nb"


def test_combine_legacy_ab():
    # Tương thích workflow lưu trước khi gộp cổng (cổng cũ a/b)
    out = CombineTextNode().run({"a": "x", "b": "y"}, {})
    assert out["text"] == "x\ny"


def test_combine_empty():
    assert CombineTextNode().run({}, {})["text"] == ""


# ---------- build_reference_block: khối tham chiếu đánh số "Ảnh N" ----------

def test_reference_block_basic():
    assert (build_reference_block(["cái áo", "người mẫu"])
            == "Ảnh đầu vào:\n- Ảnh 1: cái áo\n- Ảnh 2: người mẫu")


def test_reference_block_empty_middle_keeps_numbering():
    # Nhãn rỗng giữa → liệt kê "(không mô tả)", số KHÔNG nhảy
    out = build_reference_block(["cái áo", "", "nền"])
    assert "- Ảnh 2: (không mô tả)" in out
    assert "- Ảnh 3: nền" in out


def test_reference_block_no_labels_returns_empty():
    # Không nhãn nào có nội dung → "" (giữ prompt cũ nguyên vẹn)
    assert build_reference_block(["", ""]) == ""
    assert build_reference_block([]) == ""


def test_compose_edit_prompt_prepends_block():
    out = compose_edit_prompt(["áo", "người"], "mặc áo lên người")
    assert out.startswith("Ảnh đầu vào:")
    assert out.endswith("mặc áo lên người")


def test_compose_edit_prompt_no_labels_unchanged():
    # Backward compat: không nhãn → prompt y như cũ
    assert compose_edit_prompt([], "x") == "x"
    assert compose_edit_prompt(["", ""], "x") == "x"


# ---------- override chỉ thị hệ thống trong khối tham chiếu ----------

def test_compose_edit_prompt_default_instruction_unchanged():
    # Backward compat: có nhãn, override None → chỉ thị mặc định nguyên vẹn
    out = compose_edit_prompt(["áo", "người"], "ghép")
    assert IMAGE_REF_INSTRUCTION in out
    assert out == (build_reference_block(["áo", "người"]) + "\n"
                   + IMAGE_REF_INSTRUCTION + "\n\nghép")


def test_compose_edit_prompt_override_replaces_instruction():
    out = compose_edit_prompt(["áo", "người"], "ghép",
                              instruction_override="Chỉ đổi nền, giữ nguyên bố cục.")
    assert "Chỉ đổi nền, giữ nguyên bố cục." in out
    assert IMAGE_REF_INSTRUCTION not in out
    assert "KHÔNG tráo mặt" not in out


def test_compose_edit_prompt_blank_override_uses_default():
    # Override toàn khoảng trắng → coi như không có → giữ mặc định
    out = compose_edit_prompt(["áo", "người"], "ghép", instruction_override="   ")
    assert IMAGE_REF_INSTRUCTION in out


def test_compose_edit_prompt_no_labels_ignores_override():
    # Không nhãn → prompt nguyên, override không chèn gì
    assert compose_edit_prompt([], "x", instruction_override="Y") == "x"


def test_edit_image_has_instruction_param():
    params = {p["name"]: p for p in EditImageNode.metadata()["params"]}
    assert "instruction" in params
    assert params["instruction"]["ptype"] == "textarea"


# ---------- param "Mô tả ảnh" (is_image_label) trên node nguồn ----------

def test_load_image_has_label_param():
    params = {p["name"]: p for p in LoadImageNode.metadata()["params"]}
    assert "image_label" in params
    assert params["image_label"].get("is_image_label") is True


def test_generate_image_has_label_param():
    params = {p["name"]: p for p in GenerateImageNode.metadata()["params"]}
    assert "image_label" in params
    assert params["image_label"].get("is_image_label") is True


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
