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


def valid_dynamic_hash(blob, path):
    """Verify Android-linker hash tables and file-backed PT_LOAD locations.

    This catches absent/invalid DT_HASH and DT_GNU_HASH before distributing
    an APK, unlike generic checks of ELF machine architecture and ZIP CRC.
    """
    if len(blob) < 64 or blob[:4] != b"\x7fELF" or blob[4:6] != b"\x02\x01":
        fail("Invalid ELF64 library: " + path)
    phoff = struct.unpack_from("<Q", blob, 32)[0]
    entsize, count = struct.unpack_from("<HH", blob, 54)
    if entsize < 56 or phoff + entsize * count > len(blob):
        fail("Invalid ELF program header table: " + path)
    loads = []
    dynamics = []
    for i in range(count):
        off = phoff + i * entsize
        p_type = struct.unpack_from("<I", blob, off)[0]
        p_offset, p_vaddr, p_filesz = (
            struct.unpack_from("<Q", blob, off + 8)[0],
            struct.unpack_from("<Q", blob, off + 16)[0],
            struct.unpack_from("<Q", blob, off + 32)[0],
        )
        if p_offset + p_filesz > len(blob):
            fail("ELF segment exceeds file bounds: " + path)
        if p_type == 1:
            p_align = struct.unpack_from("<Q", blob, off + 48)[0]
            # ELF ABI requires virtual address and file offset congruence
            # modulo p_align. Android's linker also maps ELF by system pages.
            # Some patchelf-altered Termux .so files violate this despite
            # readelf reporting a DT_HASH/DT_GNU_HASH entry.
            if (p_offset - p_vaddr) % 4096 != 0:
                fail("Android ELF PT_LOAD 4K page alignment invalid: " + path)
            if p_align > 1 and (p_offset - p_vaddr) % p_align != 0:
                fail("Android ELF PT_LOAD p_align congruence invalid: " + path)
            loads.append((p_vaddr, p_vaddr + p_filesz, p_offset))
        elif p_type == 2:
            dynamics.append((p_offset, p_filesz))

    def mapped(vaddr, size):
        for start, end, offset in loads:
            if start <= vaddr and vaddr + size <= end:
                return offset + (vaddr - start)
        return None

    found = False
    for off, length in dynamics:
        if length % 16:
            fail("Malformed ELF dynamic segment: " + path)
        for at in range(off, off + length, 16):
            tag, value = struct.unpack_from("<QQ", blob, at)
            if tag == 0:
                break
            if tag not in (4, 0x6FFFFEF5):
                continue
            size = 8 if tag == 4 else 16
            position = mapped(value, size)
            if position is None:
                fail("Android ELF DT_HASH/DT_GNU_HASH points outside PT_LOAD: " + path)
            header = struct.unpack_from("<II", blob, position)
            if header[0] == 0 or header[1] == 0:
                fail("Android ELF has empty DT_HASH/DT_GNU_HASH: " + path)
            found = True
    if not found:
        fail("Android ELF missing DT_HASH/DT_GNU_HASH: " + path)


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
        valid_dynamic_hash(archive.read(path), path)
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
