"""Tests for WebSearchTool.execute() and WebFetchTool.execute() with mocked httpx."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from deep_coder.tools.web import WebFetchTool, WebSearchTool


class TestWebSearchExecute:
    async def test_empty_query(self):
        tool = WebSearchTool()
        result = await tool.execute(query="")
        assert not result.success

    async def test_successful_search(self):
        html_body = (
            '<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com">'
            "Example Title</a>"
            '<a class="result__snippet">This is a snippet</a>'
        )
        mock_resp = MagicMock()
        mock_resp.text = html_body
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_coder.tools.web.httpx.AsyncClient", return_value=mock_client):
            tool = WebSearchTool()
            result = await tool.execute(query="test query", max_results=2)
            assert result.success
            assert "Example Title" in result.content

    async def test_no_results(self):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>No results</body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_coder.tools.web.httpx.AsyncClient", return_value=mock_client):
            tool = WebSearchTool()
            result = await tool.execute(query="asdfghjkl")
            assert result.success
            assert "No results" in result.content

    async def test_timeout_retries(self):
        import httpx

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_coder.tools.web.httpx.AsyncClient", return_value=mock_client):
            with patch("deep_coder.tools.web.asyncio.sleep", new_callable=AsyncMock):
                tool = WebSearchTool()
                result = await tool.execute(query="test")
                assert not result.success
                assert "timed out" in result.content.lower()

    async def test_http_error_retries(self):
        import httpx

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_coder.tools.web.httpx.AsyncClient", return_value=mock_client):
            with patch("deep_coder.tools.web.asyncio.sleep", new_callable=AsyncMock):
                tool = WebSearchTool()
                result = await tool.execute(query="test")
                assert not result.success


class TestWebFetchExecute:
    async def test_empty_url(self):
        tool = WebFetchTool()
        result = await tool.execute(url="")
        assert not result.success

    async def test_unsupported_scheme(self):
        tool = WebFetchTool()
        result = await tool.execute(url="ftp://example.com")
        assert not result.success
        assert "Unsupported" in result.content

    async def test_no_scheme_adds_https(self):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Hello World</body></html>"
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_coder.tools.web.httpx.AsyncClient", return_value=mock_client):
            tool = WebFetchTool()
            result = await tool.execute(url="example.com")
            assert result.success
            assert "Hello World" in result.content

    async def test_fetch_html_page(self):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><p>Test content</p></body></html>"
        mock_resp.headers = {"content-type": "text/html; charset=utf-8"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_coder.tools.web.httpx.AsyncClient", return_value=mock_client):
            tool = WebFetchTool()
            result = await tool.execute(url="https://example.com")
            assert result.success
            assert "Test content" in result.content
            assert "example.com" in result.content

    async def test_fetch_plain_text(self):
        mock_resp = MagicMock()
        mock_resp.text = "Plain text content here"
        mock_resp.headers = {"content-type": "text/plain"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_coder.tools.web.httpx.AsyncClient", return_value=mock_client):
            tool = WebFetchTool()
            result = await tool.execute(url="https://example.com/data.txt")
            assert result.success
            assert "Plain text content" in result.content

    async def test_fetch_truncation(self):
        mock_resp = MagicMock()
        mock_resp.text = "x" * 100
        mock_resp.headers = {"content-type": "text/plain"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_coder.tools.web.httpx.AsyncClient", return_value=mock_client):
            tool = WebFetchTool()
            result = await tool.execute(url="https://example.com", max_chars=50)
            assert "truncated" in result.content

    async def test_fetch_timeout(self):
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_coder.tools.web.httpx.AsyncClient", return_value=mock_client):
            with patch("deep_coder.tools.web.asyncio.sleep", new_callable=AsyncMock):
                tool = WebFetchTool()
                result = await tool.execute(url="https://example.com")
                assert not result.success
                assert "timed out" in result.content.lower()
