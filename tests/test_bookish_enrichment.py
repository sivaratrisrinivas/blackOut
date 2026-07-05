import json

from blackout.bookish_enrichment import (
    PublicBooksApiContextProvider,
    build_bookish_context_from_env,
)
from blackout.workflow import NullBookishContextProvider


class JsonResponse:
    headers = {"Content-Type": "application/json"}

    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_public_books_api_context_uses_open_library_for_book_notes():
    requests = []

    def urlopen(request, timeout):
        requests.append(request.full_url)
        return JsonResponse({
            "docs": [
                {
                    "title": "Dune",
                    "author_name": ["Frank Herbert"],
                    "first_publish_year": 1965,
                }
            ]
        })

    provider = PublicBooksApiContextProvider(urlopen=urlopen)

    supplement = provider.supplement_for("Book note", "I bought Dune for tomorrow me.")

    assert requests == ["https://openlibrary.org/search.json?q=Dune&limit=1"]
    assert supplement == "Open Library: Dune by Frank Herbert, first published 1965"


def test_public_books_api_context_uses_poetrydb_for_poetry_notes():
    requests = []

    def urlopen(request, timeout):
        requests.append(request.full_url)
        return JsonResponse([
            {
                "title": "Ozymandias",
                "author": "Percy Bysshe Shelley",
                "linecount": "14",
            }
        ])

    provider = PublicBooksApiContextProvider(urlopen=urlopen)

    supplement = provider.supplement_for("Poetry note", 'poem: "Ozymandias"')

    assert requests == [
        "https://poetrydb.org/title/Ozymandias/title,author,linecount"
    ]
    assert supplement == "PoetryDB: Ozymandias by Percy Bysshe Shelley, 14 lines"


def test_bookish_context_is_opt_in_from_environment():
    assert isinstance(build_bookish_context_from_env({}), NullBookishContextProvider)

    provider = build_bookish_context_from_env({"BLACKOUT_BOOKISH_CONTEXT": "public-apis"})

    assert isinstance(provider, PublicBooksApiContextProvider)
