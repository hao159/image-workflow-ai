"""CLI chạy 1 node workflow ở terminal — test code node offline (kịch bản C).

CHẠY VỚI cwd=backend để `from app...` hoạt động (giống test_nodes.py):
  cd backend
  .venv\\Scripts\\python.exe run_node.py --type <node_type> [tùy chọn]

Ví dụ:
  python run_node.py --type enhance_prompt --param prompt="mèo" --fake
  python run_node.py --type generate_image --param provider=x --param prompt="mèo" --fake --out .
  python run_node.py --type resize --input image=in.png --param width=128 --param height=128 --out .

--param key=value   tham số node (lặp được)
--input handle=path đầu vào ẢNH: đọc file → bytes (lặp được)
--input-text h=val  đầu vào TEXT: giá trị thẳng (lặp được)
--fake              ép dùng FakeProvider (không gọi mạng, không tốn token)
--out DIR           thư mục lưu ảnh output (mặc định: thư mục hiện tại)
"""
import argparse
import sys
from pathlib import Path

from app import providers
from app.nodes import get_node_class

# Console Windows mặc định cp1252 không in được tiếng Việt → ép stdout UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001 — môi trường không hỗ trợ reconfigure thì bỏ qua
    pass


def _kv(items: list) -> dict:
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"Sai định dạng (cần key=value): {it}")
        key, value = it.split("=", 1)
        out[key] = value
    return out


def main():
    p = argparse.ArgumentParser(description="Chạy 1 node workflow offline.")
    p.add_argument("--type", required=True, help="node type (vd generate_image, resize)")
    p.add_argument("--param", action="append", default=[], help="param key=value (lặp)")
    p.add_argument("--input", action="append", default=[], help="input ảnh handle=đường_dẫn")
    p.add_argument("--input-text", action="append", default=[], help="input text handle=giá_trị")
    p.add_argument("--fake", action="store_true", help="ép dùng FakeProvider")
    p.add_argument("--out", default=".", help="thư mục lưu ảnh output")
    args = p.parse_args()

    if args.fake:
        providers.FORCE_FAKE = True

    cls = get_node_class(args.type)
    inputs: dict = {}
    for handle, path in _kv(args.input).items():
        inputs[handle] = Path(path).read_bytes()
    for handle, value in _kv(args.input_text).items():
        inputs[handle] = value

    params = cls.resolve_params(_kv(args.param))
    outputs = cls().run(inputs, params)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for handle, value in outputs.items():
        if isinstance(value, bytes):
            dest = out_dir / f"{args.type}_{handle}.png"
            dest.write_bytes(value)
            print(f"[image] {handle}: {len(value)} bytes -> {dest}")
        else:
            print(f"[text]  {handle}: {value}")


if __name__ == "__main__":
    main()
