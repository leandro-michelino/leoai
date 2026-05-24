from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def _html_to_text(html: str) -> str:
    text = TAG_RE.sub(" ", html)
    return SPACE_RE.sub(" ", text).strip()


def _validate_remote_url(url: str) -> str:
    cleaned = url.strip()
    parsed = urlparse(cleaned)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL invalida. Use apenas http:// ou https://.")
    if not parsed.netloc or not parsed.hostname:
        raise ValueError("URL invalida. Informe host valido.")
    if parsed.hostname.lower() == "localhost":
        raise ValueError("localhost nao e permitido para ingestao web.")

    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        # Hostname comum (DNS) segue permitido.
        ip = None

    if ip and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    ):
        raise ValueError("Hosts IP locais/privados nao sao permitidos para ingestao web.")

    return cleaned


def load_web_document(url: str, auth_header: str = "", timeout_seconds: int = 15) -> str:
    safe_url = _validate_remote_url(url)
    request = Request(url=safe_url, method="GET")
    request.add_header("User-Agent", "leoai-web-loader/1.0")
    if auth_header.strip():
        request.add_header("Authorization", auth_header.strip())

    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8", errors="replace")

    return _html_to_text(raw)
