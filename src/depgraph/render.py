"""Получение PNG-изображения по тексту PlantUML и сохранение файлов."""
from __future__ import annotations

import subprocess
import zlib

from depgraph.fetch import FetchError, fetch_bytes

PLANTUML_SERVER = "https://www.plantuml.com/plantuml/png/"
ALPHABET = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
)
COMPRESSION_LEVEL = 9
ZLIB_HEADER_SIZE = 2
ZLIB_TRAILER_SIZE = 4
GROUP_SIZE = 3
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JAR_TIMEOUT_SECONDS = 120
SERVER_HINT = "Можно указать локальный PlantUML: --plantuml-jar FILE.jar"


class RenderError(Exception):
    """Ошибка получения или сохранения изображения."""


def encode_group(chunk):
    """Кодирует до трёх байт в четыре символа алфавита PlantUML."""
    first, second, third = chunk + bytes(GROUP_SIZE - len(chunk))
    indexes = (
        first >> 2,
        ((first & 0x03) << 4) | (second >> 4),
        ((second & 0x0F) << 2) | (third >> 6),
        third & 0x3F,
    )
    return "".join(ALPHABET[index] for index in indexes)


def encode_plantuml(text):
    """Кодирует текст диаграммы для адреса сервера PlantUML."""
    packed = zlib.compress(text.encode("utf-8"), COMPRESSION_LEVEL)
    raw = packed[ZLIB_HEADER_SIZE:-ZLIB_TRAILER_SIZE]
    return "".join(
        encode_group(raw[start:start + GROUP_SIZE])
        for start in range(0, len(raw), GROUP_SIZE)
    )


def check_png(data):
    """Проверяет сигнатуру PNG в полученных данных."""
    if not data.startswith(PNG_SIGNATURE):
        raise RenderError("PlantUML вернул данные, не похожие на PNG")
    return data


def render_with_server(text):
    """Рисует диаграмму на сервере PlantUML (запрос GET)."""
    try:
        data = fetch_bytes(PLANTUML_SERVER + encode_plantuml(text))
    except FetchError as error:
        raise RenderError(f"{error}. {SERVER_HINT}") from None
    return check_png(data)


def render_with_jar(text, jar):
    """Рисует диаграмму локальным PlantUML: java -jar FILE.jar -pipe."""
    command = ["java", "-jar", jar, "-tpng", "-pipe", "-charset", "UTF-8"]
    try:
        done = subprocess.run(
            command, input=text.encode("utf-8"), capture_output=True,
            timeout=JAR_TIMEOUT_SECONDS, check=False,
        )
    except FileNotFoundError:
        raise RenderError("не найдена команда java: установите Java") from None
    except subprocess.TimeoutExpired:
        raise RenderError("PlantUML не уложился в отведённое время") from None
    if done.returncode:
        message = done.stderr.decode("utf-8", errors="replace").strip()
        raise RenderError(f"PlantUML завершился с ошибкой: {message}")
    return check_png(done.stdout)


def render_png(text, jar=""):
    """Возвращает PNG: локальным PlantUML, если указан jar, иначе сервером."""
    if jar:
        return render_with_jar(text, jar)
    return render_with_server(text)


def save_bytes(path, data):
    """Записывает байты в файл."""
    try:
        with open(path, "wb") as handle:
            handle.write(data)
    except OSError as error:
        raise RenderError(f"не удалось записать {path}: {error}") from None


def save_text(path, text):
    """Записывает текст в файл в кодировке UTF-8."""
    save_bytes(path, text.encode("utf-8"))
