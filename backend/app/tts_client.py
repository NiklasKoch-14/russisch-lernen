import httpx


class TtsUnavailable(Exception):
    """Der Sprachdienst antwortet nicht.

    Bewusst eine eigene Ausnahme: an der Route wird daraus ein 503, nie ein
    Serverfehler. Das Frontend liest den 503 als Signal, auf die Browserstimme
    zu wechseln.
    """


class TtsClient:
    """Anbindung an den Piper-Dienst, nach dem Muster von `ollama_client.py`."""

    def __init__(self, host: str, timeout: float = 10.0, health_timeout: float = 2.0):
        self._host = host.rstrip("/")
        self._timeout = timeout
        # Kuerzer als die Synthese: beim Start wartet das Frontend darauf.
        self._health_timeout = health_timeout
        self._transport: httpx.BaseTransport | None = None

    def _request(self, method: str, path: str, *, timeout: float, **kwargs) -> httpx.Response:
        with httpx.Client(transport=self._transport, timeout=timeout) as client:
            return client.request(method, f"{self._host}{path}", **kwargs)

    def synthesize(self, text: str) -> bytes:
        try:
            response = self._request(
                "POST", "/synthesize", timeout=self._timeout, json={"text": text}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TtsUnavailable(str(exc)) from exc
        return response.content

    def healthy(self) -> bool:
        try:
            response = self._request("GET", "/health", timeout=self._health_timeout)
            return response.status_code == 200
        except httpx.HTTPError:
            return False
