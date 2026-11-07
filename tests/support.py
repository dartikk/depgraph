"""Общие вспомогательные функции тестов: сборка архива APKINDEX."""
import gzip
import io
import tarfile

BLOCK = 512

INDEX_TEXT = """C:Q1
P:app
V:1.0-r0
D:libfoo>=2.0 so:libc.musl-x86_64.so.1 !conflict busybox missing-pkg

P:libfoo
V:2.1-r3
p:so:libfoo.so.2=2.1
D:so:libc.musl-x86_64.so.1 so:libfoo.so.2

P:musl
V:1.2.5-r0
p:so:libc.musl-x86_64.so.1=1

P:busybox
V:1.36-r1
D:so:libc.musl-x86_64.so.1
"""


def plain_archive(text):
    """tar.gz с единственным файлом APKINDEX."""
    raw = text.encode("utf-8")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo("APKINDEX")
        info.size = len(raw)
        archive.addfile(info, io.BytesIO(raw))
    return buffer.getvalue()


def signed_archive(text):
    """Как у Alpine: сначала поток с подписью без конца tar, затем индекс."""
    info = tarfile.TarInfo(".SIGN.RSA.test.rsa.pub")
    info.size = 4
    padded = b"sign" + bytes(BLOCK - info.size)
    return gzip.compress(info.tobuf() + padded) + plain_archive(text)
