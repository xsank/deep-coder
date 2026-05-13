"""Tests for tools/web.py — pure functions and tool properties."""

from __future__ import annotations

from deep_coder.tools.web import (
    WebFetchTool,
    WebSearchTool,
    _clean_ddg_url,
    _html_to_text,
)


class TestHtmlToText:
    def test_strip_tags(self):
        assert _html_to_text("<b>bold</b>") == "bold"

    def test_strip_script(self):
        html = "<div>text<script>alert('x')</script>more</div>"
        result = _html_to_text(html)
        assert "alert" not in result
        assert "text" in result
        assert "more" in result

    def test_strip_style(self):
        html = "<style>.a{color:red}</style><p>content</p>"
        result = _html_to_text(html)
        assert "color" not in result
        assert "content" in result

    def test_unescape_entities(self):
        assert _html_to_text("&amp; &lt; &gt;") == "& < >"

    def test_collapse_whitespace(self):
        result = _html_to_text("a     b     c")
        assert result == "a b c"

    def test_collapse_newlines(self):
        result = _html_to_text("a\n\n\n\n\nb")
        assert result == "a\n\nb"

    def test_empty(self):
        assert _html_to_text("") == ""

    def test_nested_tags(self):
        html = "<div><p><span>nested</span></p></div>"
        assert _html_to_text(html) == "nested"

    def test_noscript(self):
        html = "visible<noscript>hidden</noscript>also visible"
        result = _html_to_text(html)
        assert "hidden" not in result
        assert "visible" in result


class TestCleanDdgUrl:
    def test_with_uddg(self):
        url = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&rut=abc"
        result = _clean_ddg_url(url)
        assert result == "https://example.com/page"

    def test_without_uddg(self):
        url = "https://example.com/direct"
        result = _clean_ddg_url(url)
        assert result == "https://example.com/direct"

    def test_uddg_encoded(self):
        url = "//duck.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2F"
        result = _clean_ddg_url(url)
        assert result == "https://docs.python.org/3/"


class TestWebSearchTool:
    def test_properties(self):
        tool = WebSearchTool()
        assert tool.name == "web_search"
        assert tool.is_read_only is True
        assert tool.requires_approval is True
        assert "query" in tool.parameters["properties"]

    async def test_empty_query(self):
        tool = WebSearchTool()
        result = await tool.execute(query="")
        assert not result.success
        assert "empty" in result.content.lower()

    async def test_whitespace_query(self):
        tool = WebSearchTool()
        result = await tool.execute(query="   ")
        assert not result.success


class TestWebFetchTool:
    def test_properties(self):
        tool = WebFetchTool()
        assert tool.name == "web_fetch"
        assert tool.is_read_only is True
        assert tool.requires_approval is True
        assert "url" in tool.parameters["properties"]

    async def test_empty_url(self):
        tool = WebFetchTool()
        result = await tool.execute(url="")
        assert not result.success
        assert "empty" in result.content.lower()

    async def test_unsupported_scheme(self):
        tool = WebFetchTool()
        result = await tool.execute(url="ftp://example.com")
        assert not result.success
        assert "unsupported" in result.content.lower()
