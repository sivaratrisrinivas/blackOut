from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any

from blackout.workflow import BookishContextProvider, NullBookishContextProvider


class PublicBooksApiContextProvider:
    """Adds small book/poetry context using no-key APIs from public-apis."""

    def __init__(
        self,
        urlopen: Any = urllib.request.urlopen,
        timeout_seconds: int = 3,
    ) -> None:
        self._urlopen = urlopen
        self._timeout_seconds = timeout_seconds

    def supplement_for(self, source: str, body: str) -> str | None:
        if not _looks_bookish(source, body):
            return None

        query = _query_for(body)
        if not query:
            return None

        if "poem" in source.lower() or "poetry" in source.lower():
            return self._poetrydb_summary_for(query)

        return self._open_library_summary_for(query)

    def _open_library_summary_for(self, query: str) -> str | None:
        url = "https://openlibrary.org/search.json?" + urllib.parse.urlencode(
            {"q": query, "limit": "1"}
        )
        payload = self._get_json(url)
        docs = payload.get("docs") if isinstance(payload, dict) else None
        if not docs:
            return None

        first = docs[0]
        title = first.get("title")
        authors = first.get("author_name") or []
        year = first.get("first_publish_year")
        if not title:
            return None

        summary = f"Open Library: {title}"
        if authors:
            summary = f"{summary} by {authors[0]}"
        if year:
            summary = f"{summary}, first published {year}"
        return summary

    def _poetrydb_summary_for(self, query: str) -> str | None:
        encoded_title = urllib.parse.quote(query)
        url = f"https://poetrydb.org/title/{encoded_title}/title,author,linecount"
        payload = self._get_json(url)
        if not isinstance(payload, list) or not payload:
            return None

        first = payload[0]
        title = first.get("title")
        author = first.get("author")
        linecount = first.get("linecount")
        if not title:
            return None

        summary = f"PoetryDB: {title}"
        if author:
            summary = f"{summary} by {author}"
        if linecount:
            summary = f"{summary}, {linecount} lines"
        return summary

    def _get_json(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with self._urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, json.JSONDecodeError, ValueError):
            return None


def build_bookish_context_from_env(
    env: Mapping[str, str] | None = None,
) -> BookishContextProvider:
    configured_env = dict(env or os.environ)
    mode = configured_env.get("BLACKOUT_BOOKISH_CONTEXT", "").lower()
    if mode in {"public-apis", "books", "on", "1", "true"}:
        return PublicBooksApiContextProvider()
    return NullBookishContextProvider()


def _looks_bookish(source: str, body: str) -> bool:
    text = f"{source} {body}".lower()
    return any(word in text for word in ["book", "read", "reading", "poem", "poetry", "novel"])


def _query_for(body: str) -> str | None:
    quoted = re.search(r'"(?P<title>[^"]+)"', body)
    if quoted:
        return quoted.group("title").strip()

    match = re.search(
        r"\b(?:book|read|reading|poem|poetry|novel|title)\b\s*[:=-]?\s*(?P<title>.+)",
        body,
        flags=re.IGNORECASE,
    )
    if match:
        return _clean_query(match.group("title"))

    return _clean_query(body)


def _clean_query(value: str) -> str | None:
    value = re.sub(r"\$\d+(?:\.\d{2})?", "", value)
    value = re.sub(
        r"^\s*(?:i\s+)?(?:bought|ordered|saved|read|started|finished|downloaded)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\b(?:for tomorrow me|tonight|after midnight)\b",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = value.strip(" .,:;!?\"'")
    return value or None
