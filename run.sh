#!/usr/bin/env bash
# One-click cài đặt + chạy Image Workflow từ source trên Linux/macOS.
#
#   bash run.sh            # build frontend + chạy backend serve SPA, tự mở trình duyệt
#   bash run.sh --dev      # chạy dev mode (Vite 5173 + backend 8000, hot reload)
#   bash run.sh --rebuild  # ép build lại frontend dù dist đã có
#
# Tự lo: Python >=3.10, Node >=18 (qua nvm), venv + pip deps, npm deps.
# Mỗi bước ưu tiên userspace (nvm/pyenv), CHỈ fallback package manager hệ thống
# (apt/dnf/yum/brew) sau khi hỏi — không tự ý sudo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PY_MIN="3.10"
NODE_MAJOR_MIN=18
NVM_VERSION="v0.40.1"

DEV_MODE=0
REBUILD=0
for arg in "$@"; do
  case "$arg" in
    --dev) DEV_MODE=1 ;;
    --rebuild) REBUILD=1 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Bỏ qua tham số lạ: $arg" >&2 ;;
  esac
done

# ---------- helpers ----------
log()  { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31m[x]\033[0m %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

OS="$(uname -s)"
PYTHON=""
SUDO_OK=""  # cache câu trả lời cho phép sudo

ask_sudo() {
  # $1 = lý do. Trả 0 nếu user đồng ý dùng sudo, 1 nếu không.
  [ "$SUDO_OK" = "no" ] && return 1
  [ "$SUDO_OK" = "yes" ] && return 0
  if [ ! -t 0 ]; then SUDO_OK="no"; return 1; fi  # non-interactive → không sudo
  printf '\033[33m[?]\033[0m %s — cho phép dùng "sudo"? [y/N] ' "$1"
  read -r ans || true
  case "$ans" in [yY]*) SUDO_OK="yes"; return 0 ;; *) SUDO_OK="no"; return 1 ;; esac
}

pkg_mgr() {
  if have apt-get; then echo apt; elif have dnf; then echo dnf;
  elif have yum; then echo yum; elif have brew; then echo brew;
  elif have pacman; then echo pacman; elif have zypper; then echo zypper;
  else echo ""; fi
}

# ---------- Python >=3.10 ----------
py_ok() { "$1" -c 'import sys;raise SystemExit(0 if sys.version_info[:2]>=(3,10) else 1)' >/dev/null 2>&1; }

ensure_python() {
  for c in python3 python; do
    if have "$c" && py_ok "$c"; then PYTHON="$c"; fi
  done
  if [ -n "$PYTHON" ]; then log "Python OK: $("$PYTHON" --version 2>&1)"; ensure_venv_module; return; fi

  warn "Không thấy Python >=$PY_MIN. Thử cài..."
  # 1) userspace: pyenv
  if have pyenv; then
    log "Cài Python qua pyenv..."
    pyenv install -s 3.12.7 && pyenv local 3.12.7 || warn "pyenv cài thất bại"
    if have python3 && py_ok python3; then PYTHON="python3"; fi
  fi
  # 2) fallback: package manager (hỏi sudo)
  if [ -z "$PYTHON" ]; then
    local pm; pm="$(pkg_mgr)"
    case "$pm" in
      brew) brew install python@3.12 && PYTHON="python3" ;;  # brew không cần sudo
      apt)  ask_sudo "cài python3 + python3-venv qua apt" && sudo apt-get update && \
            sudo apt-get install -y python3 python3-venv python3-pip && PYTHON="python3" ;;
      dnf)  ask_sudo "cài python3 qua dnf" && sudo dnf install -y python3 python3-pip && PYTHON="python3" ;;
      yum)  ask_sudo "cài python3 qua yum" && sudo yum install -y python3 python3-pip && PYTHON="python3" ;;
      pacman) ask_sudo "cài python qua pacman" && sudo pacman -S --noconfirm python python-pip && PYTHON="python3" ;;
      zypper) ask_sudo "cài python3 qua zypper" && sudo zypper install -y python3 python3-pip && PYTHON="python3" ;;
    esac
  fi
  [ -n "$PYTHON" ] && py_ok "$PYTHON" || die "Cần Python >=$PY_MIN. Cài thủ công: https://www.python.org/downloads/ (hoặc pyenv)."
  log "Python OK: $("$PYTHON" --version 2>&1)"
  ensure_venv_module
}

ensure_venv_module() {
  # Debian/Ubuntu tách module venv ra gói riêng → kiểm tra & vá.
  "$PYTHON" -m venv --help >/dev/null 2>&1 && return
  warn "Thiếu module venv."
  if have apt-get; then
    local v; v="$("$PYTHON" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
    ask_sudo "cài python${v}-venv qua apt" && sudo apt-get install -y "python${v}-venv" python3-venv || true
  fi
  "$PYTHON" -m venv --help >/dev/null 2>&1 || die "Không dùng được 'venv'. Cài gói python3-venv tương ứng rồi chạy lại."
}

# ---------- Node >=18 (qua nvm) ----------
node_ok() { have node && [ "$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)" -ge "$NODE_MAJOR_MIN" ]; }

load_nvm() {
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1 || true
}

ensure_node() {
  if node_ok; then log "Node OK: $(node --version)"; ensure_npm; return; fi
  warn "Không thấy Node >=$NODE_MAJOR_MIN. Thử cài qua nvm (userspace)..."
  load_nvm
  if ! command -v nvm >/dev/null 2>&1; then
    log "Cài nvm $NVM_VERSION..."
    if have curl; then
      curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_VERSION/install.sh" | bash || warn "curl nvm lỗi"
    elif have wget; then
      wget -qO- "https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_VERSION/install.sh" | bash || warn "wget nvm lỗi"
    else
      warn "Thiếu curl/wget để cài nvm."
    fi
    load_nvm
  fi
  if command -v nvm >/dev/null 2>&1; then
    nvm install --lts && nvm use --lts || warn "nvm cài node lỗi"
  fi
  # fallback: package manager
  if ! node_ok; then
    local pm; pm="$(pkg_mgr)"
    case "$pm" in
      brew) brew install node ;;
      apt)  ask_sudo "cài nodejs+npm qua apt" && sudo apt-get install -y nodejs npm || true ;;
      dnf)  ask_sudo "cài nodejs qua dnf" && sudo dnf install -y nodejs || true ;;
      yum)  ask_sudo "cài nodejs qua yum" && sudo yum install -y nodejs || true ;;
      pacman) ask_sudo "cài nodejs+npm qua pacman" && sudo pacman -S --noconfirm nodejs npm || true ;;
      zypper) ask_sudo "cài nodejs qua zypper" && sudo zypper install -y nodejs npm || true ;;
    esac
  fi
  node_ok || die "Cần Node >=$NODE_MAJOR_MIN. Cài thủ công: https://nodejs.org/ hoặc nvm."
  log "Node OK: $(node --version)"
  ensure_npm
}

ensure_npm() { have npm || die "Có node nhưng thiếu npm — cài lại Node kèm npm."; }

# ---------- venv + pip ----------
VENV_DIR="$ROOT/backend/.venv"
VENV_PY="$VENV_DIR/bin/python"

setup_backend() {
  if [ ! -x "$VENV_PY" ]; then
    log "Tạo venv backend/.venv..."
    "$PYTHON" -m venv "$VENV_DIR" || die "Tạo venv thất bại."
  fi
  log "Cài Python deps..."
  "$VENV_PY" -m pip install --upgrade pip >/dev/null 2>&1 || warn "Nâng cấp pip lỗi (bỏ qua)."
  if ! "$VENV_PY" -m pip install -r "$ROOT/backend/requirements.txt"; then
    warn "pip lỗi — thử lại với mirror PyPI..."
    "$VENV_PY" -m pip install -r "$ROOT/backend/requirements.txt" \
      -i https://pypi.org/simple --retries 5 --timeout 60 \
      || die "Cài Python deps thất bại."
  fi
}

# ---------- frontend ----------
setup_frontend() {
  if [ -d "$ROOT/frontend/node_modules" ]; then
    log "npm deps đã có — bỏ qua cài."
  else
    log "Cài npm deps..."
    ( cd "$ROOT/frontend" && { npm ci 2>/dev/null || npm install; } ) || die "npm install thất bại."
  fi
  if [ "$DEV_MODE" -eq 1 ]; then return; fi
  if [ "$REBUILD" -eq 1 ] || [ ! -f "$ROOT/frontend/dist/index.html" ]; then
    log "Build frontend..."
    ( cd "$ROOT/frontend" && npm run build ) || die "Build frontend thất bại."
  else
    log "frontend/dist đã có — bỏ qua build (dùng --rebuild để build lại)."
  fi
}

# ---------- run ----------
run_app() {
  if [ "$DEV_MODE" -eq 1 ]; then
    log "Chạy DEV: backend (8000) + Vite (5173). Ctrl+C để dừng."
    "$VENV_PY" "$ROOT/backend/run_server.py" --reload &
    local back=$!
    trap 'kill $back 2>/dev/null || true' EXIT INT TERM
    ( cd "$ROOT/frontend" && npm run dev )
  else
    log "Chạy app: backend serve SPA + tự mở trình duyệt. Ctrl+C để dừng."
    exec "$VENV_PY" "$ROOT/backend/desktop_app.py"
  fi
}

ensure_python
ensure_node
setup_backend
setup_frontend
run_app
