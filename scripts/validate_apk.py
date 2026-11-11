#!/usr/bin/env python3
"""Validate ARM64 PineconeMC Android APK; does not certify playable Minecraft."""
from pathlib import Path
import hashlib
import io
import struct
import sys
import zipfile

if len(sys.argv) != 2:
    sys.exit("Usage: validate_apk.py <apk_path>")
apk = Path(sys.argv[1])
if not apk.is_file() or apk.stat().st_size < 300_000:
    sys.exit("Missing or implausibly small APK")

def fail(message):
    sys.exit("APK VALIDATION ERROR: " + message)

with zipfile.ZipFile(apk) as archive:
    bad = archive.testzip()
    if bad:
        fail("Corrupted ZIP member: " + bad)
    entries = set(archive.namelist())
    if "AndroidManifest.xml" not in entries:
        fail("Missing AndroidManifest.xml")
    for jar in ("NewLaunch.jar", "NewLaunchLegacy.jar", "JavaCheck.jar"):
        path = f"assets/jars/{jar}"
        if path not in entries:
            fail("Missing PineconeMC helper JAR: " + path)
        if not zipfile.is_zipfile(io.BytesIO(archive.read(path))):
            fail("Invalid PineconeMC helper JAR: " + path)
    all_libs = sorted(e for e in entries if e.startswith("lib/") and e.endswith(".so"))
    arm_libs = [e for e in all_libs if e.startswith("lib/arm64-v8a/")]
    if not arm_libs or len(all_libs) != len(arm_libs):
        fail("APK libraries must be exclusively ARM64")
    for path in arm_libs:
        with archive.open(path) as stream:
            header = stream.read(64)
        if len(header) < 64 or header[:4] != b"\x7fELF":
            fail("Not ELF: " + path)
        if header[4] != 2 or header[5] != 1 or struct.unpack_from("<H", header, 18)[0] != 183:
            fail("Expected ELF64 Little-Endian AArch64: " + path)
    if not any("elyprismlauncher" in path.lower() for path in arm_libs):
        fail("Original PineconeMC ARM64 library is not in the APK")
    # The independent Java subprocess must be packaged but NOT auto-loaded
    # by Qt during app startup. This does not assert any JVM is bundled.
    if "lib/arm64-v8a/libpinecone_java.so" not in arm_libs:
        fail("Missing Android ARM64 JNI subprocess libpinecone_java.so")
    if any(any(term in e.lower() for term in ("foldcraft", "fclcore", "pojavlauncher")) for e in entries):
        fail("An unrelated Android launcher was included")

sha = hashlib.sha256()
with apk.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        sha.update(chunk)
print("Valid Android ARM64 package structure:", apk.name)
print("Validated ARM64 native libraries:", len(arm_libs))
print("SHA256:", sha.hexdigest())
print("WARNING: Java SE runtime, LWJGL, Android startup and gameplay remain untested.")
