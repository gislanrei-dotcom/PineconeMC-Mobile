#!/usr/bin/env python3
"""Check that Qt's diagnostic artifact is an actual ARM64 Android APK.

This does not validate application runtime, game startup, or authentication.
"""
from pathlib import Path
import hashlib
import sys
import zipfile

if len(sys.argv) != 2:
    sys.exit("Usage: validate_apk.py <android.apk>")

apk = Path(sys.argv[1])
if not apk.is_file() or apk.stat().st_size < 300_000:
    sys.exit("APK missing or implausibly small")

with zipfile.ZipFile(apk) as archive:
    bad = archive.testzip()
    if bad:
        sys.exit("Corrupt APK entry: " + bad)
    entries = set(archive.namelist())
    if "AndroidManifest.xml" not in entries:
        sys.exit("Not an Android package: AndroidManifest.xml missing")
    native = sorted(e for e in entries if e.startswith("lib/arm64-v8a/") and e.endswith(".so"))
    if not native:
        sys.exit("No ARM64 native libraries in APK")
    if not any("elyprismlauncher" in e.lower() for e in native):
        sys.exit("PineconeMC native library missing (Qt packaging did not include our target)")
    legacy = [e for e in entries if any(token in e.lower() for token in ("foldcraft", "pojavlauncher", "fclcore"))]
    if legacy:
        sys.exit("Unexpected third-party launcher files: " + str(legacy[:8]))

print("Verified Android APK archive:", apk)
print("ARM64 libraries:", len(native))
print("PineconeMC native library:", [e for e in native if "elyprismlauncher" in e.lower()])
print("Size:", apk.stat().st_size, "bytes")
print("SHA256:", hashlib.sha256(apk.read_bytes()).hexdigest())
print("IMPORTANT: APK structure verified, not Minecraft Java execution or device startup.")
