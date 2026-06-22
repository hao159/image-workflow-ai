> **English** · [Tiếng Việt](README.vi.md)

# Image Workflow

An AI tool for generating & editing images via a **drag-and-drop node workflow** (similar to n8n): each node is a step (prompt → generate image → edit image → transform → save), connected by wires to build a pipeline.

![Workflow canvas](images/demo-work-flow-multi-node.png)

Run the workflow → each node shows its result directly on the canvas:

![Workflow after running](images/demo-work-flow-multi-node-exec.png)

Final output image (combining multiple images + prompt):

![Result image](images/result-image.png)

## Key Features

- **Drag-and-drop canvas:** build pipelines by connecting nodes, with live image previews on each node.
- **Multiple AI providers:** `gemini` (Gemini 2.5 Flash Image), `openai` (gpt-image-1), `codex`
  (ChatGPT/OAuth login, uses your ChatGPT plan quota). Each provider only needs an API key declared
  in **⚙ Settings** (or via `.env`).
- **Per-node caching:** unchanged nodes reuse their previous result (badge **⚡ cache**), skipping
  the AI call and saving tokens. Changing a param/input only reruns that node and its downstream nodes.
- **Multi-image composition:** the **Image description** field names each image and follows it into
  the Edit Image node ("wear the outfit from Image 1 on the person in Image 2").
- **Save workflows + run history** n8n-style (status, duration, result images for each run).
- **Offline testing:** the `fake` provider draws placeholder images without any network calls or token cost.
- **Light/dark theme** (System / Light / Dark), neutral flat style.

## Setup & Quick Start

The bootstrap script handles Python ≥3.10, Node ≥18, dependencies, frontend build, then launches the app and opens a browser.

```powershell
# Windows: double-click run.bat — or:
powershell -ExecutionPolicy Bypass -File run.ps1
```

```bash
# Linux / macOS:
bash run.sh
```

Append `-Dev` / `--dev` to run in dev mode, or `-Rebuild` / `--rebuild` to force a frontend rebuild.

### Manual Setup

```powershell
# Backend
python -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt

# Frontend
npm install --prefix frontend

# API key
copy .env.example .env   # fill in GEMINI_API_KEY / OPENAI_API_KEY (or enter later in ⚙ Settings)
```

```powershell
# Terminal 1 — backend (port 8000). Use this script instead of the uvicorn CLI to keep WS alive during long-running AI nodes.
backend\.venv\Scripts\python backend\run_server.py

# Terminal 2 — frontend (port 5173)
npm run dev --prefix frontend
```

Open http://localhost:5173, drag nodes from the left panel onto the canvas, connect them with wires, and click **▶ Run**.

## Package as a Desktop App

Bundle backend + frontend into **a single self-contained app** (no Python or Node required on the target machine):

```powershell
powershell -File build\build.ps1     # Windows → dist\ImageWorkflow\ImageWorkflow.exe
```
```bash
bash build/build.sh                  # macOS / Linux → dist/ImageWorkflow/ImageWorkflow
```

Double-click to run → automatically starts the server at `127.0.0.1:8000` and opens a browser. Data files
(`data.db`, `cache/`, `outputs/`...) are created next to the executable.

**Cross-platform releases:** push a tag (`git push origin v0.1.0`) → GitHub Actions builds
Windows + macOS + Linux and attaches zip files to the Release (`.github/workflows/release.yml`).

> **macOS — first run:** the app is not Apple-notarized, so macOS blocks it with a
> *"cannot verify for malware"* warning (one prompt per `.so` file). Downloaded files are flagged
> with *quarantine*. Quickest fix — **right-click `Run-ImageWorkflow.command` → Open → Open**
> (asked only once): the script removes quarantine from the entire bundle and then opens the app.
>
> Or remove quarantine manually in Terminal and then run:
>
> ```bash
> xattr -dr com.apple.quarantine ImageWorkflow   # the folder extracted from the zip
> ./ImageWorkflow/ImageWorkflow
> ```

## Available Nodes

| Node | Group | Function |
|---|---|---|
| Prompt | Input | Enter text / a prompt |
| Upload image | Input | Upload an image + **Image description** field (travels with the image into the Edit image node) |
| Merge prompts | Input | Concatenate multiple text segments into one |
| Generate image (AI) | AI | Text → image |
| Edit image (AI) | AI | Image + prompt → edited image (change background, add details, change style…) |
| Extract region (AI) | AI | Image + object description → AI locates the region → crops while preserving original pixels |
| Resize | Transform | Change dimensions |
| Filter | Transform | Grayscale / blur / sharpen… |
| Adjust color | Transform | Brightness / contrast / saturation |
| Save image | Output | Save to `outputs/` |

## Example Workflow

`Prompt("an astronaut cat") → Generate Image (gemini) → Edit Image ("change background to Mars") → Resize → Save Image`

Sample workflows are available in `workflows/` — click **📂 Open workflow** in the toolbar to load one.

## Architecture

- **Backend** (`backend/`): Python + FastAPI — workflow execution engine with topological ordering,
  progress streaming via WebSocket, per-node disk caching.
- **Frontend** (`frontend/`): React + React Flow — drag-and-drop canvas, image previews on nodes.
- **Provider** (`backend/app/providers/`): add a new provider by extending `ImageProvider`,
  implementing `generate()` + `edit()`, and registering it in `providers/__init__.py`.
- **New nodes** (`backend/app/nodes/`): extend `BaseNode`, add `@register_node`, declare
  `inputs/outputs/params` — the UI auto-generates the form, no frontend changes needed.

## License

Released under the [Apache License 2.0](LICENSE) — free to use, modify, and distribute (includes patent grant).
