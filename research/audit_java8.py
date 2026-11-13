#!/usr/bin/env python3
"""Inspect the real Android arm64 Java 8 runtime archive before considering
any integration. This program NEVER treats a tarball as a working game JVM.
The candidate is an OpenJDK component, not an Android launcher base.
"""
import hashlib
import io
import json
import os
from pathlib import PurePosixPath
import struct
import tarfile
import urllib.request

URL = "https://github.com/PojavLauncherTeam/android-openjdk-build-multiarch/releases/download/jre8-40df388/jre8-arm64-20220811-release.tar.xz"
MAX_BYTES = 100_000_000
ARCHIVE = "java8-runtime-arm64.tar.xz"

def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "PineconeMC-Mobile-audit/1"})
    with urllib.request.urlopen(req, timeout=120) as source, open(ARCHIVE, "wb") as dest:
        copied = 0
        sha = hashlib.sha256()
        while (block := source.read(2**20)):
            copied += len(block)
            if copied > MAX_BYTES:
                raise RuntimeError("Unexpectedly oversized runtime")
            dest.write(block)
            sha.update(block)
    print("SOURCE:", URL)
    print("ARCHIVE_SHA256:", sha.hexdigest())
    print("ARCHIVE_BYTES:", copied)
    names, sizes, links = [], {}, []
    with tarfile.open(ARCHIVE, mode="r:xz") as tar:
        for entry in tar:
            path = PurePosixPath(entry.name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError("Unsafe archive path " + entry.name)
            if entry.issym() or entry.islnk():
                links.append((entry.name, entry.linkname))
            elif entry.isfile():
                names.append(entry.name)
                sizes[entry.name] = entry.size
            elif not entry.isdir():
                raise RuntimeError("Unexpected tar member " + entry.name)
    print("FILES:", len(names))
    print("SYMLINKS:", len(links))
    print("TOTAL_EXTRACTED:", sum(sizes.values()))
    for name in names:
        if any(marker in name.lower() for marker in [
            "libjvm.so", "/rt.jar", "libjava.so", "libawt.so", "libfreetype.so",
            "/bin/java", "libjli.so", "libverify.so", "cacerts", "/release"
        ]):
            print("RUNTIME_FILE:", name, sizes[name])
    for link in links[:60]:
        print("LINK:", *link)
    print("FIRST_FILES:", json.dumps(names[:45]))
    if len(names) < 15 or not any(name.endswith("/libjvm.so") for name in names):
        raise RuntimeError("Java 8 JVM shared library absent")
    if not any(name.endswith("/rt.jar") for name in names):
        raise RuntimeError("Java 8 class library rt.jar absent")
    print("ARCHIVE_INVENTORY_SUCCESS: yes (device execution NOT tested)")

if __name__ == "__main__":
    main()
