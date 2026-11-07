"""Чтение индекса пакетов Alpine Linux (формат APKINDEX)."""
from __future__ import annotations

import io
import re
import tarfile
import zlib
from dataclasses import dataclass, field

from depgraph.fetch import fetch_bytes, index_url

INDEX_MEMBER = "APKINDEX"
FIELD_PATTERN = re.compile(r"^([A-Za-z]):(.*)$")
NAME_PATTERN = re.compile(r"^[^<>=~]+")
CONFLICT_PREFIX = "!"


class ApkError(Exception):
    """Ошибка чтения или разбора индекса пакетов."""


@dataclass
class ApkPackage:
    """Запись индекса: имя, версия, зависимости и предоставляемые имена."""

    name: str
    version: str
    depends: list = field(default_factory=list)
    provides: list = field(default_factory=list)


def token_name(token):
    """Выделяет имя из токена вида «name>=1.2»; конфликты дают None."""
    if token.startswith(CONFLICT_PREFIX):
        return None
    match = NAME_PATTERN.match(token)
    return match.group(0) if match else None


def names_of(value):
    """Возвращает имена из строки токенов, разделённых пробелами."""
    names = (token_name(token) for token in value.split())
    return [name for name in names if name]


def make_package(record):
    """Создаёт ApkPackage из полей записи или None, если полей не хватает."""
    if "P" not in record or "V" not in record:
        return None
    return ApkPackage(
        name=record["P"],
        version=record["V"],
        depends=names_of(record.get("D", "")),
        provides=names_of(record.get("p", "")),
    )


def add_package(packages, record):
    """Добавляет в список пакет, собранный из записи, если он корректен."""
    package = make_package(record)
    if package:
        packages.append(package)


def parse_index(text):
    """Разбирает текст APKINDEX: записи разделены пустыми строками."""
    packages, record = [], {}
    for line in text.splitlines():
        if line.strip():
            match = FIELD_PATTERN.match(line)
            if match:
                record[match.group(1)] = match.group(2)
            continue
        add_package(packages, record)
        record = {}
    add_package(packages, record)
    return packages


def extract_index_text(data):
    """Достаёт текст APKINDEX из архива APKINDEX.tar.gz."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            member = archive.extractfile(INDEX_MEMBER)
            if member is None:
                raise ApkError(f"{INDEX_MEMBER} в архиве не файл")
            return member.read().decode("utf-8", errors="replace")
    except KeyError:
        raise ApkError(f"в архиве нет файла {INDEX_MEMBER}") from None
    except (tarfile.TarError, OSError, EOFError, zlib.error) as error:
        raise ApkError(f"не удалось прочитать архив: {error}") from None


class ApkIndex:
    """Индекс пакетов репозитория с разбором зависимостей."""

    def __init__(self, packages):
        """Строит словари пакетов и поставщиков виртуальных имён."""
        self.packages = {}
        self.providers = {}
        self.selected = {}
        for package in packages:
            self.register(package)

    def register(self, package):
        """Запоминает пакет и имена, которые он предоставляет."""
        self.packages.setdefault(package.name, []).append(package)
        for name in package.provides:
            self.providers.setdefault(name, package.name)

    def check_root(self, name, version):
        """Находит пакет заданной версии; иначе бросает ApkError."""
        versions = self.packages.get(name)
        if not versions:
            raise ApkError(f"пакет {name} не найден в репозитории")
        for package in versions:
            if package.version == version:
                self.selected[name] = package
                return package
        known = ", ".join(package.version for package in versions)
        raise ApkError(
            f"пакет {name} версии {version} не найден; "
            f"в репозитории есть версии: {known}"
        )

    def current(self, name):
        """Выбранная версия пакета или последняя из индекса."""
        if name in self.selected:
            return self.selected[name]
        versions = self.packages.get(name)
        return versions[-1] if versions else None

    def resolve(self, name):
        """Имя пакета для зависимости: сам пакет или его поставщик."""
        if name in self.packages:
            return name
        return self.providers.get(name, name)

    def dependencies(self, name):
        """Прямые зависимости пакета (имена пакетов без повторов)."""
        package = self.current(name)
        if package is None:
            return []
        result = []
        for dep in package.depends:
            target = self.resolve(dep)
            if target != name and target not in result:
                result.append(target)
        return result


def load_index(repo):
    """Скачивает и разбирает индекс репозитория по его URL."""
    data = fetch_bytes(index_url(repo))
    return ApkIndex(parse_index(extract_index_text(data)))
