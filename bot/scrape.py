"""Завантаження сторінки вакансії за посиланням і витяг тексту з HTML."""
import re
from html.parser import HTMLParser

import httpx

URL_RE = re.compile(r"https?://\S+")
MAX_CHARS = 15000
SKIP_TAGS = {"script", "style", "noscript", "svg", "head", "nav", "footer"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.chunks.append(data.strip())


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return "\n".join(parser.chunks)[:MAX_CHARS]


async def fetch_page_text(url: str) -> str:
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (compatible; JobTrackerBot/1.0)"},
    ) as http:
        r = await http.get(url)
        r.raise_for_status()
        return html_to_text(r.text)
