#!/usr/bin/env python3
"""Package a verified offline Minecraft version catalog from PineconeMC's
own official upstream metadata (not a third-party launcher).

The source is pinned for reproducibility. Normal online metadata refresh and
downloads remain enabled, but the initial version selection no longer
depends on the first network request.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

REVISION = "421ab9ab51b173daf0106560bef15f3aa340ae8e"
ROOT = (
    "https://raw.githubusercontent.com/ElyPrismLauncher/meta-launcher/"
    + REVISION + "/"
)
DEST = Path("android/assets/bootstrap-meta")


def download(relative: str, max_size: int) -> bytes:
    with urlopen(ROOT + relative, timeout=90) as response:
        blob = response.read(max_size + 1)
    if not blob or len(blob) > max_size:
        raise RuntimeError(f"Invalid metadata size: {relative}")
    return blob


index_bytes = download("index.json", 256_000)
version_bytes = download("net.minecraft/index.json", 2_000_000)
index = json.loads(index_bytes)
versions = json.loads(version_bytes)
if index.get("formatVersion") != 1 or versions.get("formatVersion") != 1:
    raise RuntimeError("Unexpected upstream metadata format")
minecraft = next(
    (x for x in index.get("packages", []) if x.get("uid") == "net.minecraft"),
    None,
)
if minecraft is None:
    raise RuntimeError("Missing net.minecraft metadata")
expected_hash = minecraft.get("sha256")
actual_hash = hashlib.sha256(version_bytes).hexdigest()
if actual_hash != expected_hash:
    raise RuntimeError(f"Upstream net.minecraft hash mismatch: {actual_hash}")
count = len(versions.get("versions", []))
if count < 100:
    raise RuntimeError(f"Unexpectedly small Minecraft version catalog: {count}")
(DEST / "net.minecraft").mkdir(parents=True, exist_ok=True)
(DEST / "index.json").write_bytes(index_bytes)
(DEST / "net.minecraft" / "index.json").write_bytes(version_bytes)
print(f"Bundled {count} upstream Minecraft versions for offline list; SHA256={actual_hash}")
