---
phase: 4
title: "Fake provider + run-node CLI"
status: completed
priority: P2
effort: "0.5d"
dependencies: [1]
---

# Phase 4: Fake provider + run-node CLI

## Overview

Kịch bản C — test code node mới offline (không token): `FakeProvider` trả ảnh PNG placeholder (vẽ prompt lên nền màu) + sinh text echo; đăng ký provider `fake` để dùng trong ⚙ Cài đặt (config tên "test (fake)"). CLI `run_node.py` chạy 1 node ở terminal với input tự nhập, `--fake` ép dùng FakeProvider. Độc lập Phase 2/3 (chỉ cần Phase 1 cho engine/node API; thực ra chỉ cần node API + providers).

## Requirements

- Functional:
  - `FakeProvider(ImageProvider)`: `generate(prompt, **) → PNG bytes` (PIL: nền màu theo hash prompt + text prompt cắt ngắn); `edit(images, prompt, **)` → lấy ảnh đầu vào (hoặc nền) + nhãn → PNG; `generate_text(prompt, **) → f"[fake] {prompt[:120]}"`. `name="fake"`.
  - Đăng ký `"fake": FakeProvider` trong `PROVIDER_CLASSES`; `make_provider("fake")` → `FakeProvider()` (không cần api_key). → tự xuất hiện trong `PROVIDER_NAMES` (dropdown ⚙ Cài đặt) để tạo config offline.
  - Cờ `FORCE_FAKE` (module global ở `providers/__init__.py`): khi bật, `resolve_model_config()` trả `(FakeProvider(), "")` bất kể tên config.
  - CLI `backend/run_node.py`: `--type <node_type>` `--param k=v` (lặp) `--input handle=<path>` (lặp, đọc file → bytes) `--fake` `--out <dir>`; build inputs, `cls.resolve_params`, `cls().run(inputs, params)`, in meta từng output (image→size+đường dẫn lưu, text→giá trị), lưu image ra `--out`.
- Non-functional: file < 200 dòng; FakeProvider không gọi mạng; CLI dùng `argparse`; chạy bằng venv python (`from app...` → chạy với cwd=`backend`).

## Architecture

`providers/fake.py`:
```python
from PIL import Image, ImageDraw
from .base import ImageProvider
class FakeProvider(ImageProvider):
    name = "fake"
    def _render(self, text, base=None) -> bytes:    # nền màu hash(text) hoặc ảnh base + overlay text → PNG bytes
    def generate(self, prompt, *, model="", aspect_ratio="1:1", **o): return self._render(f"GEN: {prompt}")
    def edit(self, images, prompt, *, model="", **o): return self._render(f"EDIT: {prompt}", base=images[0] if images else None)
    def generate_text(self, prompt, *, model="", system="", **o): return f"[fake] {prompt[:120]}"
```

`providers/__init__.py`:
```python
from .fake import FakeProvider
PROVIDER_CLASSES = {..., "fake": FakeProvider}
FORCE_FAKE = False
def make_provider(name, ...): if name=="fake": return FakeProvider(); ...
def resolve_model_config(selection):
    if FORCE_FAKE: return FakeProvider(), ""
    ...  # như cũ
```

`run_node.py` (cwd=backend):
```python
import argparse; from app import providers; from app.nodes import get_node_class
args = parse(...)
if args.fake: providers.FORCE_FAKE = True
cls = get_node_class(args.type)
inputs = {handle: Path(p).read_bytes() for handle,p in args.input}   # image; text input qua --param hoặc --input-text
params = cls.resolve_params(dict(k=v ...))
out = cls().run(inputs, params)
for h,v in out.items(): print + nếu bytes → lưu args.out/{type}_{h}.png
```

## Related Code Files

- Create: `backend/app/providers/fake.py`
- Create: `backend/run_node.py`
- Create: `backend/test_fake_provider.py` (offline, `__main__` runner)
- Modify: `backend/app/providers/__init__.py` (đăng ký fake + FORCE_FAKE + nhánh make_provider/resolve)
- Read for context: `backend/app/providers/base.py`, `backend/app/nodes/generate.py` (cách node gọi provider), `backend/app/nodes/enhance_prompt.py`

## Implementation Steps

1. **Test trước** `test_fake_provider.py`:
   - `FakeProvider().generate("mèo")` → bytes, `Image.open` mở được, mode RGB.
   - `.edit([png], "đổi nền")` → bytes mở được.
   - `.generate_text("x")` → str bắt đầu "[fake]".
   - `make_provider("fake")` trả `FakeProvider`; `"fake" in PROVIDER_NAMES`.
   - `FORCE_FAKE=True` → `resolve_model_config("bất kỳ")` trả `(FakeProvider, "")` (reset về False cuối test).
2. `providers/fake.py`: implement `_render` (PIL: `Image.new` nền màu, `ImageDraw.text` prompt cắt dòng), 3 method.
3. `providers/__init__.py`: import + đăng ký + `FORCE_FAKE` + nhánh.
4. `run_node.py`: argparse, FORCE_FAKE, build inputs/params, run, in + lưu output. Hỗ trợ `--input-text handle=...` cho input text (vì `--input` đọc file bytes).
5. Chạy `backend\.venv\Scripts\python.exe test_fake_provider.py` → pass.
6. Smoke CLI: `cd backend; ..\backend\.venv\Scripts\python.exe run_node.py --type enhance_prompt --param text="mèo" --param style=... --fake` → in text; `--type generate_image --param provider="x" --param prompt="mèo" --fake --out .` → lưu PNG.

## Success Criteria

- [x] `test_fake_provider.py` pass.
- [x] Tạo config provider `fake` trong ⚙ → node `Tạo ảnh`/`Sửa ảnh`/`enhance_prompt` chạy trong UI/engine KHÔNG gọi mạng, trả ảnh/text placeholder.
- [x] `run_node.py --fake` chạy 1 node offline, in meta + lưu ảnh.
- [x] Provider thật (gemini/openai/codex) không đổi hành vi khi `FORCE_FAKE=False`.

## Risk Assessment

- **Font PIL mặc định**: dùng `ImageDraw.text` font mặc định (không cần file font) để khỏi phụ thuộc hệ thống.
- **CLI import path**: chạy với cwd=`backend` để `from app...` hoạt động (giống test_nodes.py). Ghi rõ trong `--help`/docstring.
- **FORCE_FAKE rò rỉ trạng thái** (global) → CLI dùng 1 lần rồi thoát; test phải reset `False` ở `finally`.
- **Fake xuất hiện trong dropdown cho mọi user**: vô hại (chỉ là provider dev); README ghi chú "fake = test offline".
