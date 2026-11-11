#!/usr/bin/env python3
"""Prepare a Java 17 Android runtime *candidate*, never a playable release.

Packages are fetched from Termux's official APT repository, checked with
SHA256, and extracted WITHOUT executing Debian maintainer scripts. ELF
libraries are placed in Android nativeLibs and Java data in verified assets.
"""
from pathlib import Path
import gzip
import hashlib
import re
import shutil
import struct
import subprocess
import tempfile
import urllib.request

BASE = "https://packages.termux.dev/apt/termux-main"
PIN = "48a5eddbe94e354282132578da17c1394caa04d83a4592074c1793b436ff9c15"
PACKAGES = [
    "openjdk-17", "libandroid-shmem", "libandroid-spawn", "libiconv",
    "libjpeg-turbo", "zlib", "littlecms", "alsa-lib", "alsa-plugins",
    "ca-certificates-java",
]

def digest(file):
    h = hashlib.sha256()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download(url, file):
    with urllib.request.urlopen(url, timeout=120) as response, open(file, "wb") as output:
        shutil.copyfileobj(response, output)

def index_from_gz(gz):
    records = {}
    for entry in gzip.decompress(gz).decode("utf-8").split("\n\n"):
        fields = {}
        for line in entry.splitlines():
            if ": " in line and not line.startswith(" "):
                key, value = line.split(": ", 1)
                fields[key] = value
        if fields.get("Architecture") in ("aarch64", "all") and "Package" in fields:
            records.setdefault(fields["Package"], fields)
    return records

def arm64(file):
    with open(file, "rb") as f:
        h = f.read(64)
    return len(h) >= 64 and h[:4] == b"\x7fELF" and h[4] == 2 \
        and h[5] == 1 and struct.unpack_from("<H", h, 18)[0] == 183

def main():
    output = Path("candidate").resolve()
    assets = output / "android/assets/runtime/java-17"
    libs = output / "android/libs/arm64-v8a"
    assets.mkdir(parents=True)
    libs.mkdir(parents=True)
    report = []
    manifest = []
    stored = {}
    skipped = []

    def stage_native(original, name):
        if not re.fullmatch(r"lib[A-Za-z0-9_.+-]+\.so", name):
            raise RuntimeError("Invalid native library name " + name)
        if not arm64(original):
            raise RuntimeError("Not an ARM64 ELF: " + str(original))
        orig_hash = digest(original)
        if name in stored:
            if stored[name] != orig_hash:
                raise RuntimeError("Native library basename collision: " + name)
            return
        stored[name] = orig_hash
        dest = libs / name
        shutil.copyfile(original, dest)
        subprocess.run(["patchelf", "--set-rpath", "$ORIGIN", str(dest)], check=True)

    with tempfile.TemporaryDirectory() as temp_path:
        temp = Path(temp_path)
        compressed = temp / "Packages.gz"
        download(BASE + "/dists/stable/main/binary-aarch64/Packages.gz", compressed)
        records = index_from_gz(compressed.read_bytes())
        root = temp / "root"
        root.mkdir()
        for package in PACKAGES:
            entry = records.get(package)
            if not entry:
                raise RuntimeError("Missing Termux repository package " + package)
            filename = entry["Filename"]
            checksum = entry["SHA256"]
            if not filename.startswith("pool/main/") or ".." in filename:
                raise RuntimeError("Invalid package filename")
            if not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise RuntimeError("Invalid checksum")
            if package == "openjdk-17":
                if entry["Version"] != "17.0.21-2" or checksum != PIN:
                    raise RuntimeError("Termux OpenJDK 17 pinned version changed")
            archive = temp / (package + ".deb")
            download(BASE + "/" + filename, archive)
            if digest(archive) != checksum:
                raise RuntimeError("Bad package SHA256: " + package)
            subprocess.run(["dpkg-deb", "-x", str(archive), str(root)], check=True)
            report.append(f"{package} {entry['Version']} sha256={checksum}")

        prefix = root / "data/data/com.termux/files/usr"
        jdk = prefix / "lib/jvm/java-17-openjdk"
        if not (jdk / "lib/modules").is_file():
            raise RuntimeError("JDK image lacks lib/modules")
        if not (jdk / "lib/server/libjvm.so").is_file():
            raise RuntimeError("JDK image lacks lib/server/libjvm.so")

        for path in sorted(jdk.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(jdk).as_posix()
            if rel.startswith(("bin/", "jmods/", "man/", "include/", "demo/")):
                continue
            if not path.is_file():
                skipped.append(rel + " (broken symlink or unreadable)")
                continue
            if path.name.endswith(".so") or rel == "lib/jspawnhelper":
                name = "libpinecone_jspawnhelper.so" if rel == "lib/jspawnhelper" else path.name
                stage_native(path, name)
                manifest.append(("L", rel, name))
                continue
            with open(path, "rb") as f:
                header = f.read(4)
            if header == b"\x7fELF":
                skipped.append(rel + " (unsupported executable)")
                continue
            target = assets / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            manifest.append(("F", rel, str(target.stat().st_size), digest(target)))

        for path in sorted((prefix / "lib").glob("lib*.so")):
            if path.is_file() and arm64(path):
                stage_native(path, path.name)

        (assets / "manifest.tsv").write_text(
            "# F <path> <size> <SHA256> or L <path> <libName>\n"
            + "".join("\t".join(row) + "\n" for row in sorted(manifest)),
            encoding="utf-8"
        )
        needed = set()
        for lib in libs.glob("*.so"):
            result = subprocess.run(["patchelf", "--print-needed", str(lib)],
                                    capture_output=True, text=True, check=True)
            needed.update(result.stdout.splitlines())
        system = {"libc.so", "libm.so", "libdl.so", "liblog.so", "libandroid.so",
                  "libz.so", "libEGL.so", "libGLESv2.so", "libOpenSLES.so"}
        missing = sorted(needed - set(stored) - system)
        details = [
            "Experimental OpenJDK17 ARM64 Bionic candidate - NO Android launch test",
            f"Runtime assets: {len(manifest)}",
            f"Native ELF libraries: {len(stored)}",
            f"Java modules bytes: {(assets / 'lib/modules').stat().st_size}",
            "Native libraries rewritten with $ORIGIN runpath; remaining absolute Termux",
            "prefix strings or JDK defaults are NOT fixed by this transformation.",
            "Missing ELF dependencies: " + ", ".join(missing or ["none"]),
            "Unresolved symlinks: " + "; ".join(skipped or ["none"]),
            "Java startup, HTTPS, JVM relocation and Minecraft gameplay UNTESTED.",
            "Do not distribute this candidate as a working runtime.",
            *report,
        ]
        (output / "CANDIDATE-REPORT.txt").write_text("\n".join(details) + "\n", encoding="utf-8")
        print("\n".join(details))
        if len(stored) < 20 or (assets / "lib/modules").stat().st_size < 20_000_000:
            raise RuntimeError("Candidate unexpectedly incomplete")

if __name__ == "__main__":
    main()
