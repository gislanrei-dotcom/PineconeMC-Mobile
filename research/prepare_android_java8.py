#!/usr/bin/env python3
"""Stage a checksum-verified Android/Bionic OpenJDK 8 runtime for PineconeMC.

This is a Java *component*, NOT a base from another launcher. Keep the
PineconeMC C++ launcher and JNI runner. Rename each Java 8 JNI library and
all DT_NEEDED references to coexist with OpenJDK17 in a single Android APK.
No claim of game/playability until a real Android JVM/graphics test passes.
"""
from pathlib import Path, PurePosixPath
import hashlib
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import urllib.request

URL = ("https://github.com/FahmiArrohmann/termux-java8/releases/download/v1.0/"
       "jre8-arm64-20260927-release.tar.xz")
SHA256 = "6613175678ab17ace21a41720f6ad308ebf9101236920cd4b3f5058c823b902c"
BASE = Path("candidate8/android")
ASSETS = BASE / "assets/runtime/java-8"
LIBS = BASE / "libs/arm64-v8a"
SYSTEM = {"libc.so", "libdl.so", "libm.so", "liblog.so",
          "libandroid.so", "libz.so", "libEGL.so", "libGLESv2.so",
          "libc++_shared.so"}

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def arm64(file):
    with open(file, "rb") as f:
        head = f.read(64)
    return (len(head) >= 64 and head[:4] == b"\x7fELF"
            and head[4] == 2 and struct.unpack_from("<H", head, 18)[0] == 183)

def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout

def main():
    LIBS.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive = root / "openjdk8-aarch64.tar.xz"
        with urllib.request.urlopen(
            urllib.request.Request(URL, headers={"User-Agent":"PineconeMC-Mobile/1"}),
            timeout=120,
        ) as request, archive.open("wb") as target:
            shutil.copyfileobj(request, target)
        if digest(archive) != SHA256:
            raise RuntimeError("Java 8 OpenJDK archive SHA256 mismatch")
        manifest, native_names = [], {}
        with tarfile.open(archive, mode="r:xz") as bundle:
            for entry in bundle:
                rel = PurePosixPath(entry.name)
                if rel.is_absolute() or ".." in rel.parts:
                    raise RuntimeError("Unsafe archive path: " + entry.name)
                name = str(rel)
                if entry.isdir() or entry.issym() or entry.islnk():
                    continue
                if not entry.isfile():
                    raise RuntimeError("Unexpected archive entry: " + name)
                if name.startswith(("man/", "include/", "demo/", "sample/")):
                    continue
                raw = bundle.extractfile(entry)
                if raw is None:
                    raise RuntimeError("Missing tar member: " + name)
                # Do not run unpacked executable code on Android.
                if name.startswith("bin/"):
                    continue
                dest = root / "staged" / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("wb") as out:
                    shutil.copyfileobj(raw, out)
                if arm64(dest):
                    if not dest.name.endswith(".so"):
                        if name == "lib/jexec":
                            # ELF helper for java -jar execution; the app's
                            # JNI launcher handles jar manifests directly.
                            print("Skipping optional native jexec helper")
                            continue
                        raise RuntimeError("Unexpected ELF binary: " + name)
                    original = dest.name
                    if not re.fullmatch(r"lib[A-Za-z0-9_+. -]+\.so", original):
                        raise RuntimeError("Invalid ELF library name " + original)
                    renamed = "libp8_" + original[3:]
                    if renamed in native_names:
                        if digest(native_names[renamed]) != digest(dest):
                            raise RuntimeError("Java 8 native basename collision " + name)
                    else:
                        native_names[renamed] = dest
                    manifest.append(("L", name, renamed))
                else:
                    target = ASSETS / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(dest, target)
                    manifest.append(("F", name, str(target.stat().st_size), digest(target)))
        if not (ASSETS / "lib/rt.jar").is_file():
            raise RuntimeError("Java8 rt.jar missing")
        for key in ["libp8_jvm.so", "libp8_java.so", "libp8_verify.so", "libp8_zip.so"]:
            if key not in native_names:
                raise RuntimeError("Missing OpenJDK8 native dependency " + key)
        renamed_by_original = {k.replace("libp8_", "lib", 1): k
                               for k in native_names}
        for renamed, source in sorted(native_names.items()):
            target = LIBS / renamed
            shutil.copyfile(source, target)
            needed = [line.strip() for line in run("patchelf", "--print-needed", str(target)).splitlines()]
            for original in needed:
                if original in renamed_by_original:
                    run("patchelf", "--replace-needed", original,
                        renamed_by_original[original], str(target))
                elif original not in SYSTEM:
                    raise RuntimeError(f"Unresolved Java8 native library dependency: {renamed} -> {original}")
            run("patchelf", "--set-soname", renamed, str(target))
            if not arm64(target):
                raise RuntimeError("Patched native library invalid: " + renamed)
            # Android's page loader requires congruent PT_LOAD offsets.
            with target.open("rb") as fp:
                header = fp.read(64)
                phoffset = struct.unpack_from("<Q", header, 32)[0]
                entsize, count = struct.unpack_from("<HH", header, 54)
                fp.seek(phoffset)
                table = fp.read(entsize*count)
            for i in range(count):
                off = i*entsize
                if struct.unpack_from("<I", table, off)[0] != 1: continue
                p_offset = struct.unpack_from("<Q", table, off+8)[0]
                p_vaddr = struct.unpack_from("<Q", table, off+16)[0]
                p_align = struct.unpack_from("<Q", table, off+48)[0]
                if (p_offset-p_vaddr)%4096 != 0 or (p_align > 1 and (p_offset-p_vaddr)%p_align != 0):
                    raise RuntimeError("Bad ELF LOAD alignment: " + renamed)
        (ASSETS / "manifest.tsv").write_text(
            "# OpenJDK8 native links / verified resource files\n"
            + "".join("\t".join(row)+"\n" for row in sorted(manifest)),
            encoding="utf-8"
        )
        print(f"Prepared OpenJDK8: {len(native_names)} renamed native libraries, "
              f"{len(manifest)} verified asset/link records, "
              f"{(ASSETS/'lib/rt.jar').stat().st_size} bytes rt.jar.")
        print("Staged for APK layout ONLY. Java8 boot and LWJGL rendering NOT tested.")

if __name__ == "__main__":
    main()
