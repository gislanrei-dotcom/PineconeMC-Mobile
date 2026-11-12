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
      "        QT_ANDROID_TARGET_SDK_VERSION 35\n"
      "        QT_ANDROID_VERSION_CODE 1\n"
      "        QT_ANDROID_PACKAGE_SOURCE_DIR \"${CMAKE_SOURCE_DIR}/../android\"\n"
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

# Android data and instance files must stay in the application's own writable
# files directory, not in the parent directory or the desktop installation root.
patch("launcher/Application.cpp",
      """#if defined(Q_OS_LINUX) || defined(Q_OS_FREEBSD) || defined(Q_OS_OPENBSD)
        QDir foo(FS::PathCombine(binPath, ".."));  // typically portable-root or /usr""",
      """#if defined(Q_OS_ANDROID)
        m_rootPath = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
#elif defined(Q_OS_LINUX) || defined(Q_OS_FREEBSD) || defined(Q_OS_OPENBSD)
        QDir foo(FS::PathCombine(binPath, ".."));  // typically portable-root or /usr""")

patch("launcher/Application.cpp",
      """        if (DesktopServices::isSnap()) {
            foo = QDir(qEnvironmentVariable("SNAP_USER_COMMON"));
        } else {
            foo = QDir(FS::PathCombine(QStandardPaths::writableLocation(QStandardPaths::AppDataLocation), ".."));
        }""",
      """#if defined(Q_OS_ANDROID)
        foo = QDir(QStandardPaths::writableLocation(QStandardPaths::AppDataLocation));
#else
        if (DesktopServices::isSnap()) {
            foo = QDir(qEnvironmentVariable("SNAP_USER_COMMON"));
        } else {
            foo = QDir(FS::PathCombine(QStandardPaths::writableLocation(QStandardPaths::AppDataLocation), ".."));
        }
#endif""")

# The original PineconeMC uses helper JARs from its own Java sources
# (NewLaunch/Legacy and JavaCheck). On Android APK assets aren't normal
# filesystem paths, so install them atomically under the app's private data.
patch("launcher/Application.cpp",
      """#include <QFileInfo>""",
      """#include <QFileInfo>
#include <QFile>
#include <QSaveFile>""")

patch("launcher/Application.cpp",
      """    m_dataPath = dataPath;

    /*
     * Establish the mechanism""",
      """    m_dataPath = dataPath;

#ifdef Q_OS_ANDROID
    const QString jarDir = FS::PathCombine(m_rootPath, "jars");
    if (!QDir().mkpath(jarDir)) {
        showFatalErrorMessage("Could not create the Android launcher JAR directory.", jarDir);
        return;
    }
    for (const QString& jarName : {QStringLiteral("NewLaunch.jar"),
                                   QStringLiteral("NewLaunchLegacy.jar"),
                                   QStringLiteral("JavaCheck.jar")}) {
        QFile asset(QStringLiteral("assets:/jars/") + jarName);
        if (!asset.open(QIODevice::ReadOnly)) {
            qWarning() << "Missing bundled original PineconeMC helper JAR:" << jarName;
            continue;
        }
        const QByteArray contents = asset.readAll();
        const QString destination = FS::PathCombine(jarDir, jarName);
        QFile existing(destination);
        if (existing.open(QIODevice::ReadOnly) && existing.readAll() == contents) {
            continue;
        }
        QSaveFile output(destination);
        if (!output.open(QIODevice::WriteOnly) ||
            output.write(contents) != contents.size() ||
            !output.commit()) {
            showFatalErrorMessage("Could not install bundled PineconeMC JAR.", destination);
            return;
        }
    }
#endif

    /*
     * Establish the mechanism""")

# Keep the original Pinecone instance and Java launch logic. Add native
# Android OpenJDK prerequisite checks without importing another launcher.
patch("launcher/CMakeLists.txt",
      "target_include_directories(Launcher_logic PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})",
      """target_include_directories(Launcher_logic PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
if(ANDROID)
    target_sources(Launcher_logic PRIVATE
        "${CMAKE_SOURCE_DIR}/../android/native/AndroidRuntime.cpp"
        "${CMAKE_SOURCE_DIR}/../android/native/AndroidTouchBridge.cpp")
    target_include_directories(Launcher_logic PRIVATE
        "${CMAKE_SOURCE_DIR}/../android/native")
endif()""")

patch("launcher/launch/steps/CheckJava.cpp",
      '#include "java/JavaUtils.h"',
      """#include "java/JavaUtils.h"
#ifdef Q_OS_ANDROID
#include "AndroidRuntime.h"
#endif""")
patch("launcher/launch/steps/CheckJava.cpp",
      """void CheckJava::executeTask()
{""",
      """void CheckJava::executeTask()
{
#ifdef Q_OS_ANDROID
    const auto runtime = AndroidRuntime::inspect();
    if (!runtime.available()) {
        emit logLine(runtime.error, MessageLevel::Fatal);
        emitFailed(runtime.error);
        return;
    }
    m_parent->instance()->settings()->set("JavaPath", runtime.javaExecutable);
#endif""")

# Optional separate OpenJDK process adapter based on JNI Invocation API.
# Disabled by default: no Android/Bionic Java 17 libjvm.so is bundled yet.
# This is independent PineconeMC code, not another Android launcher.
patch("launcher/CMakeLists.txt",
      "target_link_libraries(${Launcher_Name} PRIVATE Launcher_logic)",
      """target_link_libraries(${Launcher_Name} PRIVATE Launcher_logic)
if(ANDROID)
    option(PINECONE_EXPERIMENTAL_JAVA_RUNNER "Build JNI Java runner prototype" OFF)
    if(PINECONE_EXPERIMENTAL_JAVA_RUNNER)
        add_executable(pinecone_java_runner
            "${CMAKE_SOURCE_DIR}/../android/runtime/JavaRunner.cpp")
        target_compile_features(pinecone_java_runner PRIVATE cxx_std_17)
        target_link_libraries(pinecone_java_runner PRIVATE dl)
        # Package this PIE executable as a native lib filename so Android
        # 10+ can execute it from the APK's nativeLibraryDir. Do NOT use
        # QT_ANDROID_EXTRA_LIBS: Qt would dlopen() it during app startup.
        set_target_properties(pinecone_java_runner PROPERTIES
            PREFIX "lib" OUTPUT_NAME "pinecone_java" SUFFIX ".so"
            RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../android/libs/${ANDROID_ABI}")
        add_dependencies(${Launcher_Name} pinecone_java_runner)
    endif()
endif()""")

# Send the installed OpenJDK module home and APK native-library directory to
# the independent JNI subprocess while keeping PineconeMC's own launch script.
patch("launcher/minecraft/launch/LauncherPartLaunch.cpp",
      '#include "minecraft/MinecraftInstance.h"',
      """#include "minecraft/MinecraftInstance.h"
#ifdef Q_OS_ANDROID
#include "AndroidRuntime.h"
#include <QFileInfo>
#include <QProcessEnvironment>
#endif""")

patch("launcher/minecraft/launch/LauncherPartLaunch.cpp",
      "    m_process.setProcessEnvironment(instance->createLaunchEnvironment());",
      """#ifdef Q_OS_ANDROID
    QProcessEnvironment environment = instance->createLaunchEnvironment();
    const auto androidRuntime = AndroidRuntime::inspect();
    if (!androidRuntime.available()) {
        emit logLine(androidRuntime.error, MessageLevel::Fatal);
        emitFailed(androidRuntime.error);
        return;
    }
    const QString javaHome =
        QFileInfo(QFileInfo(androidRuntime.runtimeModules).absolutePath()).absolutePath();
    environment.insert("PINECONE_JAVA_HOME", javaHome);
    environment.insert("PINECONE_JVM_LIBRARY", androidRuntime.jvmLibrary);
    environment.insert("PINECONE_NATIVE_LIB_DIR", androidRuntime.nativeLibraryDirectory);
    m_process.setProcessEnvironment(environment);
#else
    m_process.setProcessEnvironment(instance->createLaunchEnvironment());
#endif""")

# The desktop wizard requests 620x660 logical pixels. On a landscape
# phone the available height can be ~400 logical pixels, so the entire
# footer (Next / Finish) is rendered offscreen. Bound the wizard to the
# ACTUAL Android viewport after it has been shown and laid out.
patch("launcher/ui/setupwizard/SetupWizard.cpp",
      '    resize(620, 660);\n    setMinimumSize(300, 400);',
      '''#ifdef Q_OS_ANDROID
    setMinimumSize(0, 0);
    // Defer until Android has attached the window to the landscape screen.
    // Qt screen coordinates are device-independent pixels, not screenshot px.
    QTimer::singleShot(0, this, [this]() {
        QScreen* display = this->screen();
        if (!display)
            display = QGuiApplication::primaryScreen();
        if (!display)
            return;
        const QSize screenSize = display->availableGeometry().size();
        const int width = qMax(260, screenSize.width() - 16);
        const int height = qMax(230, screenSize.height() - 16);
        setMaximumSize(width, height);
        resize(qMin(620, width), qMin(660, height));
        qInfo() << "PineconeMC Android wizard size" << size()
                << "available landscape area" << screenSize;
    });
#else
    resize(620, 660);
    setMinimumSize(300, 400);
#endif''')

# Qt Widgets are mouse-oriented on the desktop. Some Android devices show
# the initial language wizard but don't synthesize widget clicks from touch.
# Scope the explicit adapter to the ORIGINAL setup wizard, including its list
# viewport and navigation buttons, so normal launcher code remains untouched.
patch("launcher/ui/setupwizard/SetupWizard.cpp",
      '#include "SetupWizard.h"',
      '''#include "SetupWizard.h"
#ifdef Q_OS_ANDROID
#include "AndroidTouchBridge.h"
#include <QTimer>
#include <QScreen>
#include <QGuiApplication>
#include <QDebug>
#endif''')
patch("launcher/ui/setupwizard/SetupWizard.cpp",
      '    setObjectName(QStringLiteral("SetupWizard"));',
      '''    setObjectName(QStringLiteral("SetupWizard"));
#ifdef Q_OS_ANDROID
    auto* touchBridge = new AndroidTouchBridge(this);
    // Pages and buttons are added after constructing the QWizard; defer the
    // initial scan until the Qt event loop and repeat after navigation.
    QTimer::singleShot(0, touchBridge, [touchBridge]() { touchBridge->activate(); });
    connect(this, &QWizard::currentIdChanged, touchBridge, [touchBridge](int) {
        QTimer::singleShot(0, touchBridge, [touchBridge]() { touchBridge->activate(); });
    });
#endif''')

print("Android CMake adjustments applied to actual PineconeMC source.")
