#!/usr/bin/env python3
"""Android CMake portability patch for the official PineconeMC source.

Only changes the original PineconeMC build definitions. Never replaces its
code with another launcher. Emits precise failures if source revision changes.
"""
from pathlib import Path
import argparse

p = argparse.ArgumentParser()
p.add_argument("source", type=Path)
args = p.parse_args()
root = args.source.resolve()

def patch(path, old, new):
    f = root / path
    data = f.read_text(encoding="utf-8")
    if old not in data:
        raise SystemExit(f"ABORT: unexpected upstream layout in {path}: {old!r}")
    f.write_text(data.replace(old, new, 1), encoding="utf-8")
    print(f"Patched {path}: {old!r}")

# Qt for Android uses a shared-library target and androiddeployqt, not a
# Unix desktop executable. qt_add_executable retains the original main.cpp.
patch("launcher/CMakeLists.txt",
      "add_executable(${Launcher_Name} MACOSX_BUNDLE WIN32 main.cpp ${LAUNCHER_RCS})",
      "if(ANDROID)\n"
      "    qt_add_executable(${Launcher_Name} main.cpp ${LAUNCHER_RCS})\n"
      "    set_target_properties(${Launcher_Name} PROPERTIES\n"
      "        QT_ANDROID_PACKAGE_NAME \"ru.pineconemc.mobile\"\n"
      "        QT_ANDROID_VERSION_NAME \"0.1.0\"\n"
      "        QT_ANDROID_MIN_SDK_VERSION 28\n"
      "    )\n"
      "else()\n"
      "    add_executable(${Launcher_Name} MACOSX_BUNDLE WIN32 main.cpp ${LAUNCHER_RCS})\n"
      "endif()")

# qt_add_executable uses keyword form internally for Android packaging;
# all later calls on that target must use keyword form as well.
patch("launcher/CMakeLists.txt",
      "target_link_libraries(${Launcher_Name} Launcher_logic)",
      "target_link_libraries(${Launcher_Name} PRIVATE Launcher_logic)")

# Qt's Android build also defines Q_OS_LINUX. Feral GameMode and Linux
# desktop dlopen-based library discovery do not exist on Android.
# Preserve the Pinecone launcher logic; omit only OS-specific desktop hooks.
def exclude_desktop_gamemode(path, expected):
    f = root / path
    data = f.read_text(encoding="utf-8")
    old = "#ifdef Q_OS_LINUX"
    count = data.count(old)
    if count != expected:
        raise SystemExit(f"ABORT: expected {expected} desktop Linux blocks in {path}, got {count}")
    f.write_text(data.replace(old, "#if defined(Q_OS_LINUX) && !defined(Q_OS_ANDROID)"),
                 encoding="utf-8")
    print(f"Guarded {count} desktop Linux blocks for Android in {path}")

exclude_desktop_gamemode("launcher/Application.cpp", 3)
exclude_desktop_gamemode("launcher/minecraft/launch/LauncherPartLaunch.cpp", 2)

# Android is UNIX to CMake, but not the Linux desktop: avoid deployment of
# .desktop files/man pages, and don't link QtDBus if not packaged for Android.
patch("CMakeLists.txt",
      "find_package(Qt6 COMPONENTS DBus)\n    list(APPEND Launcher_QT_DBUS Qt6::DBus)",
      "if(NOT ANDROID)\n"
      "        find_package(Qt6 COMPONENTS DBus)\n"
      "        if(TARGET Qt6::DBus)\n"
      "            list(APPEND Launcher_QT_DBUS Qt6::DBus)\n"
      "        endif()\n"
      "    endif()")
patch("CMakeLists.txt",
      "elseif(UNIX)\n",
      "elseif(UNIX AND NOT ANDROID)\n")

# Qt 6 on Android does not transitively expose QDebug through QStringList.
# The original inline warning in this header requires QDebug's full definition.
patch("launcher/java/JavaPerformance.h",
      "#include <QStringList>",
      "#include <QDebug>\n#include <QStringList>")

print("Android CMake adjustments applied to actual PineconeMC source.")
