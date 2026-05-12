"""Web tools: search and fetch."""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from deep_coder.tools.base import Tool, ToolResult

_USER_AGENT = "Deep-Coder/1.0 (coding-assistant)"

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")

_DDG_RESULT_RE = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL,
)
_DDG_SNIPPET_RE = re.compile(
    r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
    re.DOTALL,
)


def _html_to_text(raw_html: str) -> str:
    text = _SCRIPT_STYLE_RE.sub("", raw_html)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def _clean_ddg_url(raw_url: str) -> str:
    if "uddg=" in raw_url:
        match = re.search(r"uddg=([^&]+)", raw_url)
        if match:
            return unquote(match.group(1))
    return raw_url


class WebSearchTool(Tool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web using DuckDuckGo. "
            "Returns titles, URLs, and snippets for the top results. "
            "Use for finding documentation, solutions, references, or current information."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Default: 5.",
                },
            },
            "required": ["query"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    @property
    def requires_approval(self) -> bool:
        return True

    async def execute(
        self,
        query: str,
        max_results: int = 5,
        **_: Any,
    ) -> ToolResult:
        if not query.strip():
            return ToolResult.error("Empty search query.")

        try:
            async with httpx.AsyncClient(
                timeout=15, follow_redirects=True,
            ) as client:
                resp = await client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query},
                    headers={"User-Agent": _USER_AGENT},
                )
                resp.raise_for_status()
        except httpx.TimeoutException:
            return ToolResult.error("Search timed out.")
        except httpx.HTTPError as e:
            return ToolResult.error(f"Search failed: {e}")

        body = resp.text
        titles_urls = _DDG_RESULT_RE.findall(body)
        snippets = _DDG_SNIPPET_RE.findall(body)

        if not titles_urls:
            return ToolResult.ok(f"No results found for: {query}")

        results: list[str] = []
        for i, (raw_url, raw_title) in enumerate(titles_urls[:max_results]):
            url = _clean_ddg_url(raw_url)
            title = _html_to_text(raw_title).strip() or url
            snippet = _html_to_text(snippets[i]).strip() if i < len(snippets) else ""
            entry = f"{i + 1}. [{title}]({url})"
            if snippet:
                entry += f"\n   {snippet}"
            results.append(entry)

        return ToolResult.ok(
            "\n\n".join(results),
            result_count=len(results),
        )


class WebFetchTool(Tool):
    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return (
            "Fetch a web page and extract its text content. "
            "Use for reading documentation, articles, API references, or any URL. "
            "HTML is automatically converted to plain text."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return. Default: 10000.",
                },
            },
            "required": ["url"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    @property
    def requires_approval(self) -> bool:
        return True

    async def execute(
        self,
        url: str,
        max_chars: int = 10000,
        **_: Any,
    ) -> ToolResult:
        if not url.strip():
            return ToolResult.error("Empty URL.")

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            if not parsed.scheme:
                url = f"https://{url}"
            else:
                return ToolResult.error(f"Unsupported URL scheme: {parsed.scheme}")

        try:
            async with httpx.AsyncClient(
                timeout=20, follow_redirects=True,
            ) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": _USER_AGENT},
                )
                resp.raise_for_status()
        except httpx.TimeoutException:
            return ToolResult.error(f"Fetch timed out: {url}")
        except httpx.HTTPError as e:
            return ToolResult.error(f"Fetch failed: {e}")

        content_type = resp.headers.get("content-type", "")
        raw = resp.text

        if "text/html" in content_type or raw.strip().startswith("<!"):
            text = _html_to_text(raw)
        else:
            text = raw

        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n... (truncated)"

        domain = urlparse(url).netloc
        return ToolResult.ok(
            f"Source: {url}\n\n{text}",
            domain=domain,
            chars=len(text),
        )
