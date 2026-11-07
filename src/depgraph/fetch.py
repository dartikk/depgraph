"""Загрузка данных по сети (только стандартная библиотека)."""
from __future__ import annotations

import urllib.error
import urllib.request

TIMEOUT_SECONDS = 30
INDEX_NAME = "APKINDEX.tar.gz"
USER_AGENT = "depgraph/1.0"


class FetchError(Exception):
    """Ошибка загрузки данных по URL."""


def index_url(repo):
    """Возвращает адрес архива APKINDEX по адресу репозитория."""
    if repo.endswith(INDEX_NAME):
        return repo
    return repo.rstrip("/") + "/" + INDEX_NAME


def fetch_bytes(url):
    """Скачивает содержимое URL; при сбое бросает FetchError."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as reply:
            return reply.read()
    except urllib.error.HTTPError as error:
        raise FetchError(
            f"сервер ответил кодом {error.code} на запрос {url}"
        ) from None
    except urllib.error.URLError as error:
        raise FetchError(
            f"не удалось подключиться к {url}: {error.reason}"
        ) from None
    except OSError as error:
        raise FetchError(f"ошибка чтения {url}: {error}") from None
