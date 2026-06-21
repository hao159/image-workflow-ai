# Đóng gói Image Workflow thành ImageWorkflow.exe (onedir, Windows).
#
# Cách dùng:  pwsh -File build\build.ps1   (hoặc chạy trong PowerShell)
# Yêu cầu:    backend\.venv đã cài requirements.txt; frontend đã npm install.
# Kết quả:    dist\ImageWorkflow\ImageWorkflow.exe + thư mục _internal\
#
# PowerShell 5.1 KHÔNG có '&&' → kiểm $LASTEXITCODE / $? sau mỗi bước native.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot           # project root (cha của build/)
$py = Join-Path $root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    throw "Không thấy $py — chạy: python -m venv backend\.venv; backend\.venv\Scripts\pip install -r backend\requirements.txt"
}

Write-Host "==> [1/3] Build frontend (vite)..." -ForegroundColor Cyan
npm run build --prefix (Join-Path $root "frontend")
if ($LASTEXITCODE -ne 0) { throw "npm build thất bại (exit $LASTEXITCODE)" }

Write-Host "==> [2/3] Đảm bảo PyInstaller trong venv (build-time, không vào requirements.txt)..." -ForegroundColor Cyan
& $py -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    & $py -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "pip install pyinstaller thất bại" }
}

Write-Host "==> [3/3] PyInstaller (onedir)..." -ForegroundColor Cyan
& $py -m PyInstaller (Join-Path $root "build\imageworkflow.spec") `
    --noconfirm --clean `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $root "build\pyinstaller-work")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller thất bại (exit $LASTEXITCODE)" }

$exe = Join-Path $root "dist\ImageWorkflow\ImageWorkflow.exe"
if (Test-Path $exe) {
    Write-Host "`n[OK] Đóng gói xong: $exe" -ForegroundColor Green
} else {
    throw "Không thấy exe ở $exe sau khi build"
}
