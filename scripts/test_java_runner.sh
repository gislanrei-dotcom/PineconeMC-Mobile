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
output="$(PINECONE_JVM_LIBRARY="$JVM_LIB" "$RUNNER" \
  -Dpinecone.test=it_works -cp "$TEST_DIR" TestMain alpha beta)"
grep -qx 'PINECONE_RUNNER_OK:alpha|beta' <<< "$output"
grep -qx 'PINECONE_OPTION:it_works' <<< "$output"
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
