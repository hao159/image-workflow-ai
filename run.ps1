# One-click cài đặt + chạy Image Workflow từ source trên Windows.
#
#   powershell -ExecutionPolicy Bypass -File run.ps1            # build + serve, tự mở trình duyệt
#   powershell -ExecutionPolicy Bypass -File run.ps1 -Dev       # dev mode (Vite 5173 + backend 8000)
#   powershell -ExecutionPolicy Bypass -File run.ps1 -Rebuild   # ép build lại frontend
#
# (Hoặc double-click run.bat — nó tự gọi script này với ExecutionPolicy Bypass.)
#
# Tự lo: Python >=3.10, Node >=18 (qua nvm-windows), venv + pip deps, npm deps.
# Ưu tiên userspace, fallback winget/choco. Không tự nâng quyền admin.
param(
  [switch]$Dev,
  [switch]$Rebuild
)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

# Hiển thị tiếng Việt đúng (console Windows mặc định không phải UTF-8).
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$NodeMajorMin = 18

function Log  ($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Warn ($m) { Write-Host "[!] $m" -ForegroundColor Yellow }
function Die  ($m) { Write-Host "[x] $m" -ForegroundColor Red; exit 1 }
function Have ($c) { $null -ne (Get-Command $c -ErrorAction SilentlyContinue) }

# Làm mới PATH trong phiên hiện tại (sau khi cài winget/nvm đặt PATH ở registry).
function Refresh-Path {
  $m = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $u = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = ($m, $u | Where-Object { $_ }) -join ";"
}

# ---------- Python >=3.10 ----------
$script:PyCmd = $null

function Test-Py ($exe) {
  try { & $exe -c "import sys;raise SystemExit(0 if sys.version_info[:2]>=(3,10) else 1)" 2>$null; return ($LASTEXITCODE -eq 0) }
  catch { return $false }
}

function Ensure-Python {
  # python/python3 trên PATH trước, rồi tới py launcher (-3).
  foreach ($c in @("python", "python3")) {
    if ((Have $c) -and (Test-Py $c)) { $script:PyCmd = $c; break }
  }
  if (-not $script:PyCmd -and (Have "py")) {
    try { & py -3 -c "import sys;raise SystemExit(0 if sys.version_info[:2]>=(3,10) else 1)" 2>$null
          if ($LASTEXITCODE -eq 0) { $script:PyCmd = "py -3" } } catch {}
  }
  if ($script:PyCmd) { Log "Python OK: $(Invoke-Py '--version')"; return }

  Warn "Không thấy Python >=3.10. Thử cài..."
  if (Have "winget") {
    Log "Cài Python qua winget..."
    winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
    Refresh-Path
  } elseif (Have "choco") {
    Log "Cài Python qua choco..."; choco install -y python; Refresh-Path
  }
  foreach ($c in @("python", "python3")) { if ((Have $c) -and (Test-Py $c)) { $script:PyCmd = $c; break } }
  if (-not $script:PyCmd) { Die "Cần Python >=3.10. Cài thủ công: https://www.python.org/downloads/windows/ (nhớ tick 'Add to PATH')." }
  Log "Python OK: $(Invoke-Py '--version')"
}

# Gọi python (xử lý trường hợp PyCmd = 'py -3').
function Invoke-Py {
  if ($script:PyCmd -eq "py -3") { & py -3 @args } else { & $script:PyCmd @args }
}

# ---------- Node >=18 (qua nvm-windows) ----------
function Node-Ok {
  if (-not (Have "node")) { return $false }
  try { $maj = (& node -p "process.versions.node.split('.')[0]") -as [int]; return ($maj -ge $NodeMajorMin) }
  catch { return $false }
}

function Ensure-Node {
  if (Node-Ok) { Log "Node OK: $(& node --version)"; Ensure-Npm; return }
  Warn "Không thấy Node >=$NodeMajorMin. Thử cài qua nvm-windows..."
  if (-not (Have "nvm")) {
    if (Have "winget") {
      Log "Cài nvm-windows qua winget..."
      winget install -e --id CoreyButler.NVMforWindows --silent --accept-source-agreements --accept-package-agreements
      Refresh-Path
    } elseif (Have "choco") { Log "Cài nvm qua choco..."; choco install -y nvm; Refresh-Path }
  }
  if (Have "nvm") {
    Log "nvm install lts..."; & nvm install lts; & nvm use lts; Refresh-Path
  }
  # fallback: cài Node trực tiếp
  if (-not (Node-Ok)) {
    if (Have "winget") { Log "Fallback: cài Node LTS trực tiếp qua winget..."
      winget install -e --id OpenJS.NodeJS.LTS --silent --accept-source-agreements --accept-package-agreements; Refresh-Path
    } elseif (Have "choco") { choco install -y nodejs-lts; Refresh-Path }
  }
  if (-not (Node-Ok)) { Die "Cần Node >=$NodeMajorMin. Cài thủ công: https://nodejs.org/ hoặc nvm-windows." }
  Log "Node OK: $(& node --version)"; Ensure-Npm
}

function Ensure-Npm { if (-not (Have "npm")) { Die "Có node nhưng thiếu npm — cài lại Node kèm npm." } }

# ---------- venv + pip ----------
$VenvPy = Join-Path $Root "backend\.venv\Scripts\python.exe"

function Setup-Backend {
  if (-not (Test-Path $VenvPy)) {
    Log "Tạo venv backend\.venv..."
    Invoke-Py "-m" "venv" (Join-Path $Root "backend\.venv")
    if (-not (Test-Path $VenvPy)) { Die "Tạo venv thất bại." }
  }
  Log "Cài Python deps..."
  & $VenvPy -m pip install --upgrade pip *> $null
  $req = Join-Path $Root "backend\requirements.txt"
  & $VenvPy -m pip install -r $req
  if ($LASTEXITCODE -ne 0) {
    Warn "pip lỗi — thử lại với mirror PyPI..."
    & $VenvPy -m pip install -r $req -i https://pypi.org/simple --retries 5 --timeout 60
    if ($LASTEXITCODE -ne 0) { Die "Cài Python deps thất bại." }
  }
}

# ---------- frontend ----------
function Setup-Frontend {
  if (Test-Path (Join-Path $Root "frontend\node_modules")) {
    Log "npm deps đã có — bỏ qua cài."
  } else {
    Log "Cài npm deps..."
    Push-Location (Join-Path $Root "frontend")
    try {
      & npm ci 2>$null
      if ($LASTEXITCODE -ne 0) { & npm install; if ($LASTEXITCODE -ne 0) { Die "npm install thất bại." } }
    } finally { Pop-Location }
  }

  if ($Dev) { return }
  $index = Join-Path $Root "frontend\dist\index.html"
  if ($Rebuild -or -not (Test-Path $index)) {
    Log "Build frontend..."
    Push-Location (Join-Path $Root "frontend")
    try { & npm run build; if ($LASTEXITCODE -ne 0) { Die "Build frontend thất bại." } }
    finally { Pop-Location }
  } else {
    Log "frontend\dist đã có — bỏ qua build (dùng -Rebuild để build lại)."
  }
}

# ---------- run ----------
function Run-App {
  if ($Dev) {
    Log "Chạy DEV: backend (8000) + Vite (5173). Đóng cửa sổ để dừng."
    $back = Start-Process -FilePath $VenvPy -ArgumentList @((Join-Path $Root 'backend\run_server.py'), '--reload') -PassThru
    try {
      Push-Location (Join-Path $Root "frontend"); & npm run dev
    } finally {
      Pop-Location
      if ($back -and -not $back.HasExited) { Stop-Process -Id $back.Id -Force -ErrorAction SilentlyContinue }
    }
  } else {
    Log "Chạy app: backend serve SPA + tự mở trình duyệt. Ctrl+C để dừng."
    & $VenvPy (Join-Path $Root "backend\desktop_app.py")
  }
}

Ensure-Python
Ensure-Node
Setup-Backend
Setup-Frontend
Run-App
