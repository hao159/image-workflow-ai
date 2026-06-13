import json
import random
import time
import uuid

import httpx

from .. import config
from .base import ImageProvider, ProviderError


class ComfyUIProvider(ImageProvider):
    """Gọi một server ComfyUI đang chạy (mặc định http://127.0.0.1:8188).

    Dùng template txt2img / img2img chuẩn; ckpt_name lấy từ tham số `model`
    hoặc tự chọn checkpoint đầu tiên mà server có.
    """

    name = "comfyui"
    POLL_INTERVAL = 1.0
    TIMEOUT = 600

    def __init__(self, base_url: str = ""):
        self._base_url = base_url or config.COMFYUI_URL

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self._base_url, timeout=120)

    def _first_checkpoint(self, client: httpx.Client) -> str:
        r = client.get("/object_info/CheckpointLoaderSimple")
        r.raise_for_status()
        info = r.json()["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        if not info:
            raise ProviderError("ComfyUI không có checkpoint nào trong models/checkpoints.")
        return info[0]

    def _base_graph(self, ckpt: str, prompt: str, negative: str, steps: int, cfg: float,
                    denoise: float) -> dict:
        return {
            "3": {"class_type": "KSampler", "inputs": {
                "seed": random.randint(0, 2**32 - 1), "steps": steps, "cfg": cfg,
                "sampler_name": "euler", "scheduler": "normal", "denoise": denoise,
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                "latent_image": ["5", 0]}},
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {
                "images": ["8", 0], "filename_prefix": "image-workflow"}},
        }

    def _run_graph(self, client: httpx.Client, graph: dict) -> bytes:
        r = client.post("/prompt", json={"prompt": graph, "client_id": uuid.uuid4().hex})
        if r.status_code != 200:
            raise ProviderError(f"ComfyUI từ chối workflow: {r.text[:500]}")
        prompt_id = r.json()["prompt_id"]

        deadline = time.monotonic() + self.TIMEOUT
        while time.monotonic() < deadline:
            h = client.get(f"/history/{prompt_id}")
            h.raise_for_status()
            history = h.json()
            if prompt_id in history:
                entry = history[prompt_id]
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise ProviderError(
                        f"ComfyUI báo lỗi khi chạy: {json.dumps(status)[:500]}")
                for node_output in entry.get("outputs", {}).values():
                    for img in node_output.get("images", []):
                        v = client.get("/view", params={
                            "filename": img["filename"],
                            "subfolder": img.get("subfolder", ""),
                            "type": img.get("type", "output")})
                        v.raise_for_status()
                        return v.content
            time.sleep(self.POLL_INTERVAL)
        raise ProviderError("ComfyUI chạy quá thời gian chờ.")

    def generate(self, prompt: str, *, model: str = "", aspect_ratio: str = "1:1",
                 negative_prompt: str = "", steps: int = 20, cfg: float = 7.0,
                 width: int = 1024, height: int = 1024, **options) -> bytes:
        try:
            with self._client() as client:
                ckpt = model or self._first_checkpoint(client)
                graph = self._base_graph(ckpt, prompt, negative_prompt, steps, cfg, 1.0)
                graph["5"] = {"class_type": "EmptyLatentImage", "inputs": {
                    "width": width, "height": height, "batch_size": 1}}
                return self._run_graph(client, graph)
        except httpx.ConnectError as e:
            raise ProviderError(
                f"Không kết nối được ComfyUI tại {self._base_url}. "
                f"Hãy chắc chắn ComfyUI đang chạy.") from e

    def edit(self, images: list[bytes], prompt: str, *, model: str = "",
             negative_prompt: str = "", steps: int = 20, cfg: float = 7.0,
             denoise: float = 0.6, **options) -> bytes:
        try:
            with self._client() as client:
                up = client.post("/upload/image", files={
                    "image": (f"input_{uuid.uuid4().hex}.png", images[0], "image/png")})
                up.raise_for_status()
                uploaded_name = up.json()["name"]

                ckpt = model or self._first_checkpoint(client)
                graph = self._base_graph(ckpt, prompt, negative_prompt, steps, cfg, denoise)
                graph["10"] = {"class_type": "LoadImage", "inputs": {"image": uploaded_name}}
                graph["11"] = {"class_type": "VAEEncode", "inputs": {
                    "pixels": ["10", 0], "vae": ["4", 2]}}
                graph["3"]["inputs"]["latent_image"] = ["11", 0]
                return self._run_graph(client, graph)
        except httpx.ConnectError as e:
            raise ProviderError(
                f"Không kết nối được ComfyUI tại {self._base_url}. "
                f"Hãy chắc chắn ComfyUI đang chạy.") from e
