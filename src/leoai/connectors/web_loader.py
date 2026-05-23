from __future__ import annotations

import re
from urllib.request import Request, urlopen


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def _html_to_text(html: str) -> str:
    text = TAG_RE.sub(" ", html)
    return SPACE_RE.sub(" ", text).strip()


def load_web_document(url: str, auth_header: str = "", timeout_seconds: int = 15) -> str:
    request = Request(url=url, method="GET")
    if auth_header.strip():
        request.add_header("Authorization", auth_header.strip())

    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8", errors="replace")

    return _html_to_text(raw)

