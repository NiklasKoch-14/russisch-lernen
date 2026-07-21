import httpx


class OllamaClient:
    def __init__(self, host: str, model: str, timeout: float = 60.0):
        self._host = host.rstrip("/")
        self._model = model
        self._timeout = timeout

    def chat(self, messages: list[dict[str, str]]) -> str:
        response = httpx.post(
            f"{self._host}/api/chat",
            json={"model": self._model, "messages": messages, "stream": False},
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
