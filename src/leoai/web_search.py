from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


DUCKDUCKGO_API = "https://api.duckduckgo.com/"


def _collect_related_topics(data: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for entry in data:
        if "Topics" in entry and isinstance(entry["Topics"], list):
            items.extend(_collect_related_topics(entry["Topics"]))
            continue

        text = str(entry.get("Text", "")).strip()
        url = str(entry.get("FirstURL", "")).strip()
        if text and url:
            items.append({"text": text, "url": url})
    return items


def search_web_context(query: str, max_results: int = 5, timeout: int = 8) -> str:
    params = urlencode(
        {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "0",
        }
    )
    url = f"{DUCKDUCKGO_API}?{params}"

    with urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    lines: list[str] = []
    abstract = str(payload.get("AbstractText", "")).strip()
    abstract_url = str(payload.get("AbstractURL", "")).strip()

    if abstract:
        if abstract_url:
            lines.append(f"- {abstract} (fonte: {abstract_url})")
        else:
            lines.append(f"- {abstract}")

    related = _collect_related_topics(payload.get("RelatedTopics", []))
    for item in related[:max_results]:
        lines.append(f"- {item['text']} (fonte: {item['url']})")

    if not lines:
        return "Nenhum resultado web relevante encontrado."

    return "\n".join(lines)
