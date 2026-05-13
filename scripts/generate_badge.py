#!/usr/bin/env python3
"""Generate a coverage badge SVG from coverage.xml."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

BADGE_TEMPLATE = """\
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20">
  <linearGradient id="a" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <rect rx="3" width="{width}" height="20" fill="#555"/>
  <rect rx="3" x="62" width="{value_width}" height="20" fill="{color}"/>
  <rect rx="3" width="{width}" height="20" fill="url(#a)"/>
  <g fill="#fff" text-anchor="middle"
     font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="32" y="15" fill="#010101" fill-opacity=".3">coverage</text>
    <text x="32" y="14">coverage</text>
    <text x="{value_x}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{value_x}" y="14">{value}</text>
  </g>
</svg>
"""


def get_coverage(path: str = "coverage.xml") -> int:
    tree = ET.parse(path)
    rate = float(tree.getroot().get("line-rate", "0"))
    return int(rate * 100)


def get_color(pct: int) -> str:
    if pct >= 90:
        return "#4c1"
    if pct >= 75:
        return "#a3c51c"
    if pct >= 60:
        return "#dfb317"
    if pct >= 40:
        return "#fe7d37"
    return "#e05d44"


def generate_svg(pct: int) -> str:
    value = f"{pct}%"
    value_width = 44
    width = 62 + value_width
    value_x = 62 + value_width // 2
    return BADGE_TEMPLATE.format(
        width=width,
        value_width=value_width,
        value_x=value_x,
        color=get_color(pct),
        value=value,
    )


def main() -> None:
    pct = get_coverage()
    svg = generate_svg(pct)
    out = Path("assets/coverage-badge.svg")
    out.parent.mkdir(exist_ok=True)
    out.write_text(svg)
    print(f"Coverage: {pct}% -> {out}")


if __name__ == "__main__":
    main()
