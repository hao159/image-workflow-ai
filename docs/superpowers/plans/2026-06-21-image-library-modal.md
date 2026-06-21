# Image Library Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a toolbar-launched "Thư viện ảnh" modal to browse, view full-res, and delete input (`uploads/`) and output (`outputs/`) images, with client-side paging and a custom confirm popup.

**Architecture:** Backend gains 4 thin endpoints (list + delete for uploads/outputs) reusing the existing `_safe_file` guard. Frontend adds a reusable `ConfirmDialog`, an `ImageLibraryModal` (2 tabs, thumbnail grid, paging) that reuses the existing `ImageViewerModal` lightbox and `ToastContext`, plus a toolbar button in `App.jsx`.

**Tech Stack:** Python/FastAPI (backend), React + Vite (frontend), plain CSS.

## Global Constraints

- Keep each code file under 200 lines; one clear responsibility per file.
- Use kebab-case for new JS files; snake_case for Python.
- No native `window.confirm` for this feature — use the custom `ConfirmDialog`.
- No rename feature (dropped: upload files are referenced by filename in saved workflows).
- Image extensions allowed: `png, jpg, jpeg, webp, gif, bmp`.
- Backend test runner: `backend\.venv\Scripts\python.exe -m pytest <path> -q`.
- UI text in Vietnamese, matching existing copy.

---

### Task 1: Backend list + delete endpoints

**Files:**
- Modify: `backend/app/main.py` (add helper + 4 routes after the `/api/cache-image/{sha}` route, ~line 201)
- Test: `backend/test_image_library.py` (create)

**Interfaces:**
- Produces (HTTP):
  - `GET /api/uploads` → `[{name: str, url: str, size: int, modified: str}]`, newest-first
  - `GET /api/outputs` → same shape, newest-first
  - `DELETE /api/uploads/{name}` → `{"deleted": name}` or 404 `{"error": "..."}`
  - `DELETE /api/outputs/{name}` → `{"deleted": name}` or 404
- Consumes: existing `config.UPLOADS_DIR`, `config.OUTPUTS_DIR`, `_safe_file(directory, name)`.

- [ ] **Step 1: Write the failing test**

Create `backend/test_image_library.py`:

```python
"""Test thư viện ảnh: list uploads/outputs (lọc ảnh, mới nhất trước) + delete an toàn.
Dùng thư mục tạm (monkeypatch config) + TestClient, KHÔNG cần backend chạy sẵn.

Chạy: backend\\.venv\\Scripts\\python.exe -m pytest backend/test_image_library.py -q
"""
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import config
    up = tmp_path / "uploads"; up.mkdir()
    out = tmp_path / "outputs"; out.mkdir()
    monkeypatch.setattr(config, "UPLOADS_DIR", up)
    monkeypatch.setattr(config, "OUTPUTS_DIR", out)
    from app.main import app
    return TestClient(app)


def test_list_uploads_filters_and_sorts_newest_first(client):
    from app import config
    a = config.UPLOADS_DIR / "a.png"; a.write_bytes(b"x")
    b = config.UPLOADS_DIR / "b.jpg"; b.write_bytes(b"yy")
    (config.UPLOADS_DIR / "notes.txt").write_text("skip")  # không phải ảnh → bỏ
    os.utime(a, (1000, 1000))  # a cũ hơn
    os.utime(b, (2000, 2000))  # b mới hơn

    r = client.get("/api/uploads")
    assert r.status_code == 200
    data = r.json()
    assert [it["name"] for it in data] == ["b.jpg", "a.png"]  # mới nhất trước
    assert data[0]["url"] == "/api/uploads/b.jpg"
    assert data[0]["size"] == 2
    assert "modified" in data[0]


def test_delete_output_removes_file(client):
    from app import config
    f = config.OUTPUTS_DIR / "result.png"; f.write_bytes(b"z")
    r = client.delete("/api/outputs/result.png")
    assert r.status_code == 200
    assert r.json()["deleted"] == "result.png"
    assert not f.exists()


def test_delete_missing_returns_404(client):
    r = client.delete("/api/uploads/nope.png")
    assert r.status_code == 404


def test_delete_path_traversal_rejected(client):
    r = client.delete("/api/uploads/..%2f..%2fsecret.txt")
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/test_image_library.py -q`
Expected: FAIL (404 on GET `/api/uploads` — route not defined yet, or list assertion errors).

- [ ] **Step 3: Add helper + routes in `backend/app/main.py`**

Insert immediately after the `get_cache_image` function (after `return FileResponse(path, media_type="image/png")`, ~line 201):

```python
_IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}


def _list_images(directory, url_prefix: str):
    # Liệt kê file ảnh trong thư mục → mới nhất trước (theo mtime). Bỏ file không phải ảnh.
    items = []
    for p in directory.iterdir():
        if not p.is_file() or p.suffix.lower().lstrip(".") not in _IMAGE_EXTS:
            continue
        st = p.stat()
        items.append({
            "name": p.name,
            "url": f"{url_prefix}/{p.name}",
            "size": st.st_size,
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
            "_mtime": st.st_mtime,
        })
    items.sort(key=lambda x: x["_mtime"], reverse=True)
    for it in items:
        del it["_mtime"]
    return items


@app.get("/api/uploads")
def list_uploads():
    return _list_images(config.UPLOADS_DIR, "/api/uploads")


@app.get("/api/outputs")
def list_outputs():
    return _list_images(config.OUTPUTS_DIR, "/api/outputs")


@app.delete("/api/uploads/{name}")
def delete_upload(name: str):
    path = _safe_file(config.UPLOADS_DIR, name)
    if not path:
        return JSONResponse({"error": "Không tìm thấy file."}, status_code=404)
    path.unlink()
    return {"deleted": name}


@app.delete("/api/outputs/{name}")
def delete_output(name: str):
    path = _safe_file(config.OUTPUTS_DIR, name)
    if not path:
        return JSONResponse({"error": "Không tìm thấy file."}, status_code=404)
    path.unlink()
    return {"deleted": name}
```

(`time` is already imported at the top of `main.py`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/test_image_library.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/test_image_library.py
git commit -m "feat: add list + delete endpoints for uploads/outputs images"
```

---

### Task 2: Frontend API wrappers

**Files:**
- Modify: `frontend/src/api.js` (append after `clearCache`, ~line 123)

**Interfaces:**
- Consumes (HTTP): the 4 endpoints from Task 1.
- Produces (JS): `listUploads()`, `listOutputs()`, `deleteUpload(name)`, `deleteOutput(name)` — each returns the parsed JSON, throws `Error` on non-OK.

- [ ] **Step 1: Add the wrappers**

Append to `frontend/src/api.js`:

```javascript
// ---------- Thư viện ảnh (uploads/outputs) ----------

export async function listUploads() {
  const res = await fetch('/api/uploads')
  if (!res.ok) throw new Error('Không tải được danh sách ảnh đầu vào.')
  return res.json()
}

export async function listOutputs() {
  const res = await fetch('/api/outputs')
  if (!res.ok) throw new Error('Không tải được danh sách ảnh đầu ra.')
  return res.json()
}

export async function deleteUpload(name) {
  const res = await fetch(`/api/uploads/${encodeURIComponent(name)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Xóa ảnh thất bại.')
  return res.json()
}

export async function deleteOutput(name) {
  const res = await fetch(`/api/outputs/${encodeURIComponent(name)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Xóa ảnh thất bại.')
  return res.json()
}
```

- [ ] **Step 2: Verify no syntax error**

Run: `npm run build --prefix frontend`
Expected: build succeeds (no parse error). (Or `npx --prefix frontend vite build`.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.js
git commit -m "feat: add image library API wrappers"
```

---

### Task 3: ConfirmDialog component

**Files:**
- Create: `frontend/src/components/confirm-dialog.jsx`
- Create: `frontend/src/styles/image-library.css` (also holds modal grid styles used in Task 4)
- Modify: `frontend/src/styles.css` (add `@import`)

**Interfaces:**
- Produces (JS): default export `ConfirmDialog({ message, confirmLabel='Xóa', danger=true, onConfirm, onCancel })` — renders an overlay; Esc / backdrop / "Hủy" call `onCancel`; confirm button calls `onConfirm`.

- [ ] **Step 1: Create `frontend/src/components/confirm-dialog.jsx`**

```jsx
import { useEffect } from 'react'

// Popup xác nhận dùng chung (thay window.confirm). Esc / backdrop / Hủy = hủy.
export default function ConfirmDialog({
  message,
  confirmLabel = 'Xóa',
  danger = true,
  onConfirm,
  onCancel,
}) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  return (
    <div className="modal-backdrop confirm-backdrop" onClick={onCancel}>
      <div
        className="confirm-dialog"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="confirm-msg">{message}</div>
        <div className="confirm-actions">
          <button className="btn ghost" onClick={onCancel}>Hủy</button>
          <button className={`btn${danger ? ' danger' : ''}`} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/styles/image-library.css`**

```css
/* Thư viện ảnh: modal + lưới thumbnail + popup xác nhận. Phong cách trung tính, phẳng. */
.modal.img-library {
  width: min(780px, 92vw);
  max-height: 84vh;
  display: flex;
  flex-direction: column;
}

.img-library-note {
  padding: 6px 14px;
  font-size: 12px;
  opacity: 0.7;
}

.img-library-body {
  overflow-y: auto;
  padding: 12px 14px;
  flex: 1;
}

.img-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.img-card {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border, #2a2a2a);
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface-2, #1b1b1b);
}

.img-card-thumb {
  all: unset;
  cursor: pointer;
  display: block;
  aspect-ratio: 1 / 1;
  background: var(--surface, #111);
}

.img-card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.img-card-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
}

.img-card-name {
  flex: 1;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Popup xác nhận — nổi trên modal thư viện. */
.confirm-backdrop { z-index: 1000; }

.confirm-dialog {
  background: var(--surface-2, #1b1b1b);
  border: 1px solid var(--border, #2a2a2a);
  border-radius: 10px;
  padding: 18px 20px;
  min-width: 280px;
  max-width: 90vw;
}

.confirm-msg { margin-bottom: 16px; font-size: 14px; }
.confirm-actions { display: flex; justify-content: flex-end; gap: 8px; }
```

(CSS uses fallback values so it renders even if a palette var name differs; align var names with `frontend/src/styles/palette.css` if exact tokens are preferred.)

- [ ] **Step 3: Register the stylesheet in `frontend/src/styles.css`**

Add after the `workflow-browser-modal.css` import line:

```css
@import './styles/image-library.css';
```

- [ ] **Step 4: Verify build**

Run: `npm run build --prefix frontend`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/confirm-dialog.jsx frontend/src/styles/image-library.css frontend/src/styles.css
git commit -m "feat: add reusable ConfirmDialog + image library styles"
```

---

### Task 4: ImageLibraryModal component

**Files:**
- Create: `frontend/src/components/image-library-modal.jsx`

**Interfaces:**
- Consumes: `listUploads/listOutputs/deleteUpload/deleteOutput` (Task 2), `useImageViewer()` (`{ openViewer }` from `../ImageViewerContext.jsx`), `useToast()` (`../ToastContext.jsx`), `ConfirmDialog` (Task 3), `ImageIcon/TrashIcon/XIcon` (`./icons.jsx`).
- Produces (JS): default export `ImageLibraryModal({ onClose })`.

- [ ] **Step 1: Create `frontend/src/components/image-library-modal.jsx`**

```jsx
import { useCallback, useEffect, useMemo, useState } from 'react'
import { ImageIcon, TrashIcon, XIcon } from './icons.jsx'
import { listUploads, listOutputs, deleteUpload, deleteOutput } from '../api.js'
import { useImageViewer } from '../ImageViewerContext.jsx'
import { useToast } from '../ToastContext.jsx'
import ConfirmDialog from './confirm-dialog.jsx'

const PAGE_SIZE = 12 // số thumbnail mỗi trang (paging client-side)

// Cấu hình 2 tab: nhãn + hàm list/delete tương ứng.
const TABS = {
  uploads: { label: 'Đầu vào', list: listUploads, del: deleteUpload },
  outputs: { label: 'Đầu ra', list: listOutputs, del: deleteOutput },
}

// Modal thư viện ảnh: 2 tab (uploads/outputs), lưới thumbnail có paging,
// click ảnh → lightbox dùng chung, xóa qua popup xác nhận (ConfirmDialog).
export default function ImageLibraryModal({ onClose }) {
  const [tab, setTab] = useState('uploads')
  const [items, setItems] = useState([])
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [pending, setPending] = useState(null) // { name } chờ xác nhận xóa
  const { openViewer } = useImageViewer()
  const toast = useToast()

  const refresh = useCallback(async (which) => {
    setLoading(true)
    try {
      setItems(await TABS[which].list())
    } catch (e) {
      toast.error(e.message)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [toast])

  // Đổi tab → reset trang + nạp danh sách tab đó.
  useEffect(() => { setPage(0); refresh(tab) }, [tab, refresh])

  // Esc đóng modal (trừ khi đang mở popup xác nhận — Esc đó để hủy popup).
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && !pending) onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, pending])

  const pageCount = Math.max(1, Math.ceil(items.length / PAGE_SIZE))
  const safePage = Math.min(page, pageCount - 1)
  const rows = useMemo(
    () => items.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE),
    [items, safePage],
  )

  const doDelete = async () => {
    const name = pending.name
    setPending(null)
    try {
      await TABS[tab].del(name)
      toast.success('Đã xóa ảnh.')
      refresh(tab)
    } catch (e) {
      toast.error(e.message)
    }
  }

  return (
    <>
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal img-library" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <span className="modal-title"><ImageIcon size={16} /> Thư viện ảnh</span>
            <button className="btn ghost" onClick={onClose}><XIcon size={15} /></button>
          </div>

          <div className="wf-browser-tabs" role="tablist">
            {Object.entries(TABS).map(([key, t]) => (
              <button
                key={key}
                className={`wf-tab${tab === key ? ' active' : ''}`}
                onClick={() => setTab(key)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === 'uploads' && (
            <div className="img-library-note">
              Xóa ảnh đầu vào có thể làm hỏng workflow đã lưu đang dùng ảnh đó.
            </div>
          )}

          <div className="img-library-body">
            {loading ? (
              <div className="wf-browser-empty">Đang tải…</div>
            ) : items.length === 0 ? (
              <div className="wf-browser-empty">Chưa có ảnh nào.</div>
            ) : (
              <div className="img-grid">
                {rows.map((it) => (
                  <div className="img-card" key={it.name}>
                    <button
                      className="img-card-thumb"
                      title="Xem ảnh full-res"
                      onClick={() => openViewer({ src: it.url, filename: it.name })}
                    >
                      <img src={it.url} alt={it.name} loading="lazy" />
                    </button>
                    <div className="img-card-foot">
                      <span className="img-card-name" title={it.name}>{it.name}</span>
                      <button
                        className="btn ghost danger"
                        title="Xóa ảnh"
                        onClick={() => setPending({ name: it.name })}
                      >
                        <TrashIcon size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {pageCount > 1 && (
              <div className="wf-pager">
                <button className="btn ghost" disabled={safePage === 0}
                  onClick={() => setPage(safePage - 1)}>‹ Trước</button>
                <span className="wf-pager-info">Trang {safePage + 1}/{pageCount}</span>
                <button className="btn ghost" disabled={safePage >= pageCount - 1}
                  onClick={() => setPage(safePage + 1)}>Sau ›</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {pending && (
        <ConfirmDialog
          message={`Xóa ảnh "${pending.name}"?`}
          onConfirm={doDelete}
          onCancel={() => setPending(null)}
        />
      )}
    </>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `npm run build --prefix frontend`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/image-library-modal.jsx
git commit -m "feat: add image library modal with tabs, grid, paging"
```

---

### Task 5: Wire the toolbar button in App.jsx

**Files:**
- Modify: `frontend/src/App.jsx` (import, state, toolbar button, modal render)

**Interfaces:**
- Consumes: `ImageLibraryModal` (Task 4), `ImageIcon` (already imported in App.jsx via `./components/icons.jsx`? verify — if not, add to the icon import).

- [ ] **Step 1: Add the import**

Near the other component imports (after the `WorkflowBrowserModal` import, ~line 15):

```jsx
import ImageLibraryModal from './components/image-library-modal.jsx'
```

Ensure `ImageIcon` is in the icons import block (the one that includes `FolderIcon`, ~line 27). If absent, add `ImageIcon,` to that destructured import.

- [ ] **Step 2: Add state**

Find where `showWorkflowBrowser` state is declared (search `showWorkflowBrowser`) and add alongside it:

```jsx
const [showImageLibrary, setShowImageLibrary] = useState(false)
```

- [ ] **Step 3: Add the toolbar button**

In the toolbar, immediately after the "Mở workflow" button (the `<button>` ending `<FolderIcon size={14} /> Mở workflow</button>`, ~line 611):

```jsx
          <button className="btn" onClick={() => setShowImageLibrary(true)}>
            <ImageIcon size={14} /> Thư viện ảnh
          </button>
```

- [ ] **Step 4: Render the modal**

After the `{showWorkflowBrowser && (...)}` block (~line 707), add:

```jsx
      {showImageLibrary && (
        <ImageLibraryModal onClose={() => setShowImageLibrary(false)} />
      )}
```

(This sits inside the existing `<ImageViewerProvider>` tree, so `openViewer` works.)

- [ ] **Step 5: Verify build**

Run: `npm run build --prefix frontend`
Expected: build succeeds.

- [ ] **Step 6: Manual smoke test**

Start backend + frontend (or `run.ps1 -Dev`). Then:
1. Click **🖼 Thư viện ảnh** → modal opens on **Đầu vào** tab.
2. Upload an image elsewhere / confirm existing uploads + outputs render as thumbnails.
3. Click a thumbnail → lightbox opens full-res with "Tải ảnh gốc".
4. Switch to **Đầu ra** tab → outputs listed.
5. Click 🗑 on a card → ConfirmDialog popup → "Hủy" cancels, "Xóa" deletes + toast + list refreshes.
6. With >12 images, pager shows and navigates.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add Thư viện ảnh toolbar button + modal wiring"
```

---

## Self-Review

**Spec coverage:**
- 2 tabs (uploads/outputs) → Task 4 `TABS`. ✓
- List/view/delete → Tasks 1,2,4. ✓
- View full-res reuse lightbox → Task 4 `openViewer`. ✓
- Paging (12/page) → Task 4 `PAGE_SIZE`. ✓
- Custom confirm popup → Task 3 `ConfirmDialog`, used in Task 4. ✓
- Toolbar entry point → Task 5. ✓
- Đầu vào warning line → Task 4 `.img-library-note`. ✓
- No rename → not implemented (correct). ✓
- Path-traversal safety → Task 1 `_safe_file` + test. ✓
- Error handling via toast → Task 4. ✓
- Backend test → Task 1. ✓

**Placeholder scan:** none — all steps contain full code/commands.

**Type consistency:** list item shape `{name,url,size,modified}` consistent across Task 1 (backend), Task 4 (`it.name`, `it.url`). `ConfirmDialog` props (`message,onConfirm,onCancel`) consistent between Task 3 definition and Task 4 usage. `TABS[key].{list,del}` consistent.

## Open questions

None.
