# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec — đóng gói backend + SPA thành ImageWorkflow.exe.

Chạy qua build/build.ps1 (đã build frontend trước). Entry = backend/desktop_app.py.
onedir (KHÔNG --onefile): khởi động nhanh, ít bị antivirus chặn.
"""
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

# SPECPATH = thư mục chứa file .spec (build/). Project root = cha của nó.
ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
BACKEND = os.path.join(ROOT, "backend")

# Cho collect_submodules('app') tìm thấy package app lúc eval spec.
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# Nhúng frontend build vào bundle tại 'frontend_dist' (khớp config.SPA_DIR khi frozen).
datas = [(os.path.join(ROOT, "frontend", "dist"), "frontend_dist")]
binaries = []

# Node/provider được import tĩnh trong app/__init__ nhưng vẫn gom rõ cho chắc.
hiddenimports = collect_submodules("app")

# uvicorn nạp loop/protocol bằng chuỗi → static analysis dễ bỏ sót.
hiddenimports += collect_submodules("uvicorn")
hiddenimports += ["websockets", "httptools", "multipart", "anyio"]

# SDK + chứng chỉ TLS: gom cả submodule lẫn data files.
for pkg in ("google.genai", "openai", "certifi"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [os.path.join(BACKEND, "desktop_app.py")],
    pathex=[BACKEND],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageWorkflow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # giữ True khi build lần đầu để thấy lỗi; Phase 4 cân nhắc tắt
    disable_windowed_traceback=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ImageWorkflow",
)
