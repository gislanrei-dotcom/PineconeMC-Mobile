#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Qt 6.8.3 for Android requires an OpenSSL 3 runtime for HTTPS.
# Pin audited upstream KDAB Android OpenSSL binaries and verify their exact
# Git blob IDs against the pinned repository tree before including in the APK.
set -euo pipefail

REV=b71f1470962019bd89534a2919f5925f93bc5779
BASE="https://raw.githubusercontent.com/KDAB/android_openssl/${REV}"
DEST="android/libs/arm64-v8a"
LICENSE_DEST="android/assets/licenses"
mkdir -p "$DEST" "$LICENSE_DEST"

download_checked() {
  local path="$1" out="$2" blob="$3"
  curl --fail --location --silent --show-error --retry 4 --retry-all-errors     "$BASE/$path" --output "$out"
  local actual
  actual="$(git hash-object "$out")"
  if [[ "$actual" != "$blob" ]]; then
    printf 'ERROR: unexpected Git blob hash for %s: %s != %s\n' "$path" "$actual" "$blob" >&2
    exit 1
  fi
}
download_checked "ssl_3/arm64-v8a/libcrypto_3.so" "$DEST/libcrypto_3.so" "3de4dc69811ad9e75d45cceb165e47c1bddb67ff"
download_checked "ssl_3/arm64-v8a/libssl_3.so" "$DEST/libssl_3.so" "80ca3428df94b73d84e803df95c4b53b42b3acb2"
download_checked "LICENSE" "$LICENSE_DEST/KDAB-Android-OpenSSL-LICENSE.txt" "49cc83d2ee29d13453188217f0e4edd70c7f842f"

READELF="${ANDROID_HOME}/ndk/26.1.10909125/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf"
for lib in "$DEST/libcrypto_3.so" "$DEST/libssl_3.so"; do
  test -s "$lib"
  "$READELF" -h "$lib" | grep -F "AArch64"
  "$READELF" -d "$lib" | grep -F 'SONAME'
done
"$READELF" -d "$DEST/libssl_3.so" | grep -F 'libcrypto_3.so'
printf '%s\n' "Pinned arm64 OpenSSL 3 libraries and their LICENSE verified."
