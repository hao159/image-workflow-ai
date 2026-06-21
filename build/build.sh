#!/usr/bin/env bash
# Đóng gói Image Workflow thành thư mục dist/ImageWorkflow (onedir) trên Linux/macOS.
# Tương đương build/build.ps1 cho Windows — dùng CHUNG build/imageworkflow.spec.
#
# Cách dùng:  bash build/build.sh
# Yêu cầu:    backend/.venv đã cài requirements.txt; frontend đã npm install.
# Kết quả:    dist/ImageWorkflow/ImageWorkflow + thư mục _internal/
set -euo pipefail

# Thư mục chứa script là build/ → project root là cha của nó.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"

if [ ! -x "$PY" ]; then
    echo "Không thấy $PY — chạy:" >&2
    echo "  python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt" >&2
    exit 1
fi

echo "==> [1/3] Build frontend (vite)..."
npm run build --prefix "$ROOT/frontend"

echo "==> [2/3] Đảm bảo PyInstaller trong venv (build-time, không vào requirements.txt)..."
if ! "$PY" -m PyInstaller --version >/dev/null 2>&1; then
    "$PY" -m pip install pyinstaller
fi

echo "==> [3/3] PyInstaller (onedir)..."
"$PY" -m PyInstaller "$ROOT/build/imageworkflow.spec" \
    --noconfirm --clean \
    --distpath "$ROOT/dist" \
    --workpath "$ROOT/build/pyinstaller-work"

BIN="$ROOT/dist/ImageWorkflow/ImageWorkflow"

# macOS: ad-hoc ký để app chạy được trên Apple Silicon (arm64 BẮT BUỘC mọi mach-O có
# chữ ký mới nạp được). Ký mã lồng bên trong (.so/.dylib) trước rồi mới ký binary chính.
# LƯU Ý: ad-hoc KHÔNG vượt Gatekeeper cho file tải về — người dùng vẫn phải gỡ cờ
# quarantine một lần: xattr -dr com.apple.quarantine ImageWorkflow (xem README).
if [ "$(uname)" = "Darwin" ]; then
    echo "==> [macOS] Ad-hoc code signing..."
    find "$ROOT/dist/ImageWorkflow" -type f \( -name '*.so' -o -name '*.dylib' \) \
        -exec codesign --force --sign - {} + || true
    codesign --force --sign - "$BIN" || true
    # Kèm script double-click: chuột phải → Open 1 lần để gỡ quarantine toàn bộ bundle
    # rồi chạy app (tránh hàng loạt prompt cho từng .so/.dylib). Xem README.
    cp "$ROOT/build/macos-launch.command" "$ROOT/dist/ImageWorkflow/Run-ImageWorkflow.command"
    chmod +x "$ROOT/dist/ImageWorkflow/Run-ImageWorkflow.command"
fi

if [ -f "$BIN" ]; then
    echo ""
    echo "[OK] Đóng gói xong: $BIN"
else
    echo "Không thấy binary ở $BIN sau khi build" >&2
    exit 1
fi
