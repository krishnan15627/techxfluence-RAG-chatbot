"""
ollama_llm.py - the "G" (Generation) part of RAG.

Talks to a LOCAL Ollama server (default http://localhost:11434).
No API key, no cloud, no payment. Uses only the `requests` library.

Change the model or server address with environment variables:
    set OLLAMA_MODEL=llama3.2
    set OLLAMA_HOST=http://localhost:11434
"""

from __future__ import annotations

import json
import os
from typing import Iterator

import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2")


class OllamaError(Exception):
    """Raised with a beginner-friendly message when Ollama cannot answer."""


def get_status(host: str = OLLAMA_HOST, model: str = MODEL_NAME) -> dict:
    """Check if the Ollama server is running and the model is downloaded."""
    try:
        resp = requests.get(f"{host}/api/tags", timeout=3)
        resp.raise_for_status()
        names = [m.get("name", "") for m in resp.json().get("models", [])]
    except requests.exceptions.RequestException:
        return {"running": False, "model_ready": False, "models": [], "model": model}
    wanted = model.split(":")[0]
    ready = any(n == model or n.split(":")[0] == wanted for n in names)
    return {"running": True, "model_ready": ready, "models": names, "model": model}


def stream_answer(
    prompt: str,
    system: str,
    history: list[dict] | None = None,
    host: str = OLLAMA_HOST,
    model: str = MODEL_NAME,
) -> Iterator[str]:
    """Yield the answer piece by piece (streaming) from the local model."""
    messages = [{"role": "system", "content": system}]
    for m in (history or [])[-4:]:  # a little memory of the last 2 exchanges
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        # Low temperature = factual, less creative answers.
        "options": {"temperature": 0.1, "num_ctx": 4096},
    }
    try:
        with requests.post(f"{host}/api/chat", json=payload, stream=True, timeout=(5, 300)) as resp:
            if resp.status_code == 404:
                raise OllamaError(
                    f"Model '{model}' is not downloaded yet. Run this in a terminal:  ollama pull {model}"
                )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise OllamaError(data["error"])
                piece = data.get("message", {}).get("content", "")
                if piece:
                    yield piece
                if data.get("done"):
                    break
    except requests.exceptions.ConnectionError:
        raise OllamaError(
            "Cannot reach Ollama. Open the Ollama app (or run `ollama serve` in a terminal) and try again."
        )
    except requests.exceptions.Timeout:
        raise OllamaError("Ollama took too long to respond. The first answer can be slow - please try again.")
    except requests.exceptions.RequestException as exc:
        raise OllamaError(f"Ollama request failed: {exc}")
