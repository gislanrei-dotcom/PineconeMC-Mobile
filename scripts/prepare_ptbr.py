#!/usr/bin/env python3
"""Bundle an offline Brazilian Portuguese Qt translation for PineconeMC Mobile.

The upstream Prism Launcher translation is Apache-2.0 licensed and remains
separate from the GPL-3.0 launcher source. Only compiled Qt message catalogs
are packaged; no alternate launcher implementation is imported.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.request import urlopen
import xml.etree.ElementTree as ET

# Pin the exact reviewed source so Action builds remain reproducible.
REVISION = "e19b817803388123f1a04cc346424d92686c941b"
URL = (
    "https://raw.githubusercontent.com/PrismLauncher/Translations/"
    + REVISION + "/pt_BR.ts"
)
BASE = Path("android/assets/translations")
BASE.mkdir(parents=True, exist_ok=True)

with urlopen(URL, timeout=90) as response:
    ts_bytes = response.read()
if len(ts_bytes) < 100_000:
    raise RuntimeError("Brazilian Portuguese translation missing or truncated")
root = ET.fromstring(ts_bytes)
if root.attrib.get("language") not in ("pt_BR", "pt-BR"):
    raise RuntimeError("Translation is not Brazilian Portuguese")

all_msgs = root.findall(".//message")
finished = 0
unfinished = 0
for msg in all_msgs:
    tr = msg.find("translation")
    if tr is not None and tr.attrib.get("type") not in ("unfinished", "obsolete", "vanished"):
        finished += 1
    else:
        unfinished += 1

with tempfile.TemporaryDirectory() as temp:
    ts = Path(temp) / "pt_BR.ts"
    ts.write_bytes(ts_bytes)
    qm = BASE / "mmc_pt_BR.qm"
    subprocess.run(
        ["/usr/lib/qt6/bin/lrelease", str(ts), "-qm", str(qm)], check=True
    )

catalog = BASE / "mmc_pt_BR.qm"
data = catalog.read_bytes()
if len(data) < 5_000:
    raise RuntimeError("Qt translation catalog is too small")
index = {
    "file_type": "MMC-TRANSLATION-INDEX",
    "version": 2,
    "languages": {
        "pt_BR": {
            "file": "mmc_pt_BR.qm",
            "sha1": hashlib.sha1(data).hexdigest(),
            "size": len(data),
            "translated": finished,
            "untranslated": unfinished,
            "fuzzy": 0,
        }
    },
}
(BASE / "index_v2.json").write_text(
    json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(
    f"pt_BR bundled: {len(data)} bytes, {finished}/{len(all_msgs)} "
    f"source messages finished; SHA256={hashlib.sha256(data).hexdigest()}"
)
