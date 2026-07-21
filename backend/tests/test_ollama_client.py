from unittest.mock import MagicMock, patch

from app.ollama_client import OllamaClient


def test_chat_posts_to_ollama_and_returns_message_content():
    client = OllamaClient(host="http://ollama:11434", model="llama3.2:3b")
    fake_response = MagicMock()
    fake_response.json.return_value = {"message": {"role": "assistant", "content": "Hello!"}}
    fake_response.raise_for_status.return_value = None

    with patch("app.ollama_client.httpx.post", return_value=fake_response) as mock_post:
        result = client.chat([{"role": "user", "content": "Hi"}])

    assert result == "Hello!"
    mock_post.assert_called_once()
    called_kwargs = mock_post.call_args.kwargs
    assert called_kwargs["json"]["model"] == "llama3.2:3b"
    assert called_kwargs["json"]["messages"] == [{"role": "user", "content": "Hi"}]
    assert called_kwargs["json"]["stream"] is False


def test_chat_raises_on_http_error():
    import httpx

    client = OllamaClient(host="http://ollama:11434", model="llama3.2:3b")
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with patch("app.ollama_client.httpx.post", return_value=fake_response):
        try:
            client.chat([{"role": "user", "content": "Hi"}])
            assert False, "expected HTTPStatusError"
        except httpx.HTTPStatusError:
            pass
