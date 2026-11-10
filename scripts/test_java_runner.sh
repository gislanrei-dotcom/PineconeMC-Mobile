#!/usr/bin/env bash
# Linux-host regression test for the independent PineconeMC JNI launcher.
# Does not prove Android compatibility or Minecraft gameplay.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UPSTREAM="$ROOT/PineconeMC"
command -v javac >/dev/null || { echo "Host JDK javac is missing" >&2; exit 2; }
JAVA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT
JVM_LIB="$JAVA_HOME/lib/server/libjvm.so"
test -f "$JAVA_HOME/include/jni.h"
test -f "$JVM_LIB"
test -f "$UPSTREAM/libraries/javacheck/JavaCheck.java"
c++ -std=c++17 -Wall -Wextra -Werror \
  -I"$JAVA_HOME/include" -I"$JAVA_HOME/include/linux" \
  "$ROOT/android/runtime/JavaRunner.cpp" -o "$TEST_DIR/java_runner" -ldl
javac -d "$TEST_DIR" \
  "$ROOT/scripts/tests/TestMain.java" \
  "$UPSTREAM/libraries/javacheck/JavaCheck.java"
(cd "$TEST_DIR" && jar cf JavaCheck.jar JavaCheck.class)
RUNNER="$TEST_DIR/java_runner"
output="$(PINECONE_JVM_LIBRARY="$JVM_LIB" PINECONE_JAVA_HOME="$JAVA_HOME" PINECONE_NATIVE_LIB_DIR="$TEST_DIR/native" "$RUNNER" \
  -Dpinecone.test=it_works -Djava.library.path=/minecraft/natives -cp "$TEST_DIR" TestMain alpha beta)"
grep -qx 'PINECONE_RUNNER_OK:alpha|beta' <<< "$output"
grep -qx 'PINECONE_OPTION:it_works' <<< "$output"
grep -qx "PINECONE_JAVA_HOME:$JAVA_HOME" <<< "$output"
grep -qx "PINECONE_NATIVE_PATH:$TEST_DIR/native:/minecraft/natives" <<< "$output"
# Validate UTF-8 input including supplementary Unicode via code points.
# Console encodings on Linux runners are not guaranteed to be UTF-8.
unicode_output="$(PINECONE_JVM_LIBRARY="$JVM_LIB" "$RUNNER" -cp "$TEST_DIR" TestMain 'coração' '🎮')"
grep -qx 'PINECONE_UNICODE_CODEPOINTS:63,6f,72,61,e7,e3,6f|1f3ae' <<< "$unicode_output"
check="$(PINECONE_JVM_LIBRARY="$JVM_LIB" "$RUNNER" -jar "$TEST_DIR/JavaCheck.jar")"
grep -q '^os.arch=' <<< "$check"
grep -q '^java.version=' <<< "$check"
grep -q '^java.vendor=' <<< "$check"
set +e
PINECONE_JVM_LIBRARY="$JVM_LIB" "$RUNNER" --invalid-option > "$TEST_DIR/invalid.log" 2>&1
bad_arg_status=$?
PINECONE_JVM_LIBRARY="$TEST_DIR/missing.so" "$RUNNER" -cp "$TEST_DIR" TestMain > "$TEST_DIR/missing.log" 2>&1
missing_jvm_status=$?
set -e
test "$bad_arg_status" -eq 64
test "$missing_jvm_status" -eq 70
printf '%s\n' \
  'PASS: Java classpath, Java arguments and main class' \
  'PASS: original PineconeMC JavaCheck.jar through JNI' \
  'PASS: invalid CLI and missing JVM statuses' \
  'Scope: Linux host only, Android game runtime still untested'
