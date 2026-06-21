# Image Library Modal (Thư viện ảnh) — Design Spec

**Date:** 2026-06-21
**Branch:** feat/neutral-theme-redesign
**Status:** Approved design, pending spec review → implementation plan

## Goal

A toolbar-launched modal letting the user browse, view (full-res), and delete the
app's images, split into two tabs:

- **Đầu vào** — uploaded input images (`uploads/` dir, served `/api/uploads/{name}`)
- **Đầu ra** — saved output images (`outputs/` dir, served `/api/outputs/{name}`)

## Scope decisions (confirmed with user)

- **In scope:** list, view full-res (reuse existing lightbox), delete per-file, client-side paging.
- **Out of scope:** rename (dropped — upload files are referenced by filename inside saved
  workflows, so renaming the physical file breaks those references; user chose to skip it).
- **Confirm UX:** custom popup `ConfirmDialog` component (NOT native `window.confirm`).
- **Entry point:** new `🖼 Thư viện ảnh` toolbar button next to `📂 Mở workflow`.

## Backend — `backend/app/main.py`

Add 4 endpoints. Reuse the existing `_safe_file()` path-traversal guard for deletes.

| Method | Route | Behavior |
|---|---|---|
| `GET` | `/api/uploads` | List uploads dir → `[{name, url, size, modified}]`, newest first |
| `GET` | `/api/outputs` | List outputs dir → same shape, newest first |
| `DELETE` | `/api/uploads/{name}` | Delete one upload file (404 if missing) |
| `DELETE` | `/api/outputs/{name}` | Delete one output file (404 if missing) |

DRY helper `_list_images(directory, url_prefix)`:
- Scan dir, keep only image extensions (`png/jpg/jpeg/webp/gif/bmp`).
- For each: `name`, `url=f"{url_prefix}/{name}"`, `size` (bytes), `modified` (mtime, ISO or epoch).
- Sort by mtime descending (newest first).

Delete handlers: resolve via `_safe_file`; if found, `unlink()` and return `{"deleted": name}`;
else 404 JSON consistent with existing handlers.

## Frontend

### `api.js` — 4 new wrappers (existing fetch-wrapper style)
- `listUploads()` → `GET /api/uploads`
- `listOutputs()` → `GET /api/outputs`
- `deleteUpload(name)` → `DELETE /api/uploads/{name}`
- `deleteOutput(name)` → `DELETE /api/outputs/{name}`

### `components/confirm-dialog.jsx` (new, reusable)
- Props: `{ message, confirmLabel='Xóa', danger=true, onConfirm, onCancel }`.
- Modal overlay (Esc / backdrop / Hủy = cancel). Confirm button triggers `onConfirm`.
- Flat/neutral theme styling; reuses existing `.modal-backdrop` / `.modal` shell where sensible.

### `components/image-library-modal.jsx` (new, < 200 lines)
- Same modal shell + tab pattern as `workflow-browser-modal.jsx`.
- Two tabs: **Đầu vào** | **Đầu ra**. Each tab independently loads its list on open / after delete.
- Body = CSS grid of thumbnail cards. Each card:
  - `<img>` thumbnail (loads via the file `url`); click → `useImageViewer().openViewer({src: url, filename: name})`.
  - filename label (truncated).
  - 🗑 delete button → opens `ConfirmDialog`; on confirm → call delete API → refresh that tab's list → toast success.
- **Paging:** client-side, `PAGE_SIZE = 12`, pager identical to workflow-browser (`‹ Trước` / `Trang n/m` / `Sau ›`). Page resets to 0 on tab switch and after delete if page now out of range.
- Empty-state message per tab ("Chưa có ảnh nào.").
- Đầu vào tab shows a short warning line: deleting an input image may break saved workflows that reference it.

### `App.jsx`
- Add `🖼 Thư viện ảnh` toolbar button next to `📂 Mở workflow`.
- Add `showImageLibrary` state; render `<ImageLibraryModal>` inside the existing
  `ImageViewerProvider` tree (so the lightbox works from within the modal).

### `styles/image-library.css` (new)
- Grid layout for thumbnail cards, neutral/flat theme (no glow). Imported via `styles.css` or `main.jsx` per existing convention.

### `icons.jsx`
- Add `ImageIcon` if not already present.

## Data flow

1. User clicks `🖼 Thư viện ảnh` → modal opens, active tab fetches its list (`listUploads`/`listOutputs`).
2. Grid renders current page of thumbnails (sorted newest-first).
3. Click thumbnail → existing `ImageViewerModal` lightbox (full-res + download original + new tab).
4. Click 🗑 → `ConfirmDialog` → confirm → delete API → re-fetch list → toast.

## Error handling

- List/delete failures → toast error (reuse `ToastContext`).
- Backend deletes guarded by `_safe_file` (path traversal); 404 on missing file.
- Broken thumbnail (file deleted out-of-band) → `<img>` onError shows placeholder/hides card gracefully.

## Testing

- Backend: extend `backend/test_*` (e.g. a new `test_image_library.py`) — list returns expected
  shape sorted newest-first; delete removes file + 404 on missing; path traversal rejected.
- Frontend: manual smoke (no existing FE test harness) — open modal, both tabs, view, delete + confirm, paging.

## Modularization / file-size

- New components each single-purpose, < 200 lines. `confirm-dialog.jsx` reusable beyond this feature.
- Backend additions small; keep within `main.py` alongside sibling upload/output routes.

## Open questions

- None.
