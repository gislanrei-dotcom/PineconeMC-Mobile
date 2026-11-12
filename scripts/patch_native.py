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

# Android uses an in-APK Java SE runtime, not a desktop JRE installed by
# the user. Do not send mobile users to the desktop Java selection wizard
# (which will always show "No versions are currently available").
# The real game launch still calls AndroidRuntime::inspect() through CheckJava,
# so skipping the PC-only configuration does NOT bypass runtime validation.
patch("launcher/Application.cpp",
      '    bool languageRequired = settings()->get("Language").toString().isEmpty();',
      '''#ifdef Q_OS_ANDROID
    javaRequired = false;
    askjava = false;
    settings()->set("IgnoreJavaWizard", true);
    settings()->set("AutomaticJavaSwitch", false);
    settings()->set("AutomaticJavaDownload", false);
    // Previous desktop-derived defaults can allocate ~5 GiB to Minecraft on
    // a phone. Keep a conservative initial heap while allowing later changes.
    const int configuredMaxMemory = settings()->get("MaxMemAlloc").toInt();
    if (configuredMaxMemory < 512 || configuredMaxMemory > 3072) {
        settings()->set("MaxMemAlloc", 2048);
    }
    const int configuredMinMemory = settings()->get("MinMemAlloc").toInt();
    if (configuredMinMemory < 256 ||
        configuredMinMemory > settings()->get("MaxMemAlloc").toInt()) {
        settings()->set("MinMemAlloc", 512);
    }
    qInfo() << "PineconeMC Android: skip desktop Java wizard;"
               " embedded Java runtime will be checked at game launch.";
#endif
    bool languageRequired = settings()->get("Language").toString().isEmpty();''')


# Seed the official upstream Minecraft version index on a fresh Android
# install. The existing Meta::BaseEntity code still verifies/refreshes online
# content as usual, but a carrier/firewall/network timeout cannot leave the
# New Instance list completely empty on first launch.
patch("launcher/Application.cpp",
      '        m_translations.reset(new TranslationsModel("translations"));',
      '''#ifdef Q_OS_ANDROID
        QDir().mkpath(QStringLiteral("meta/net.minecraft"));
        for (const QString& relative : {QStringLiteral("index.json"),
                                        QStringLiteral("net.minecraft/index.json")}) {
            const QString destination = QStringLiteral("meta/") + relative;
            if (QFile::exists(destination) && QFileInfo(destination).size() > 1000)
                continue;
            QFile source(QStringLiteral("assets:/bootstrap-meta/") + relative);
            if (!source.open(QIODevice::ReadOnly)) {
                qWarning() << "PineconeMC Android: no bundled Minecraft catalog" << relative;
                continue;
            }
            const QByteArray bytes = source.readAll();
            QSaveFile target(destination);
            if (!target.open(QIODevice::WriteOnly) ||
                target.write(bytes) != bytes.size() || !target.commit()) {
                qWarning() << "PineconeMC Android: cannot seed Minecraft metadata" << destination;
            } else {
                qInfo() << "PineconeMC Android: installed official Minecraft metadata" << destination;
            }
        }
#endif
        m_translations.reset(new TranslationsModel("translations"));''')

# Preinstall the official-derived Brazilian Portuguese Qt catalog in the
# application's real translations directory BEFORE TranslationsModel starts.
# Without an index file, upstream reloadLocalFiles() returns early and shows
# only American English. Both assets are produced by prepare_ptbr.py.
patch("launcher/Application.cpp",
      '        m_translations.reset(new TranslationsModel("translations"));',
      '''#ifdef Q_OS_ANDROID
        QDir().mkpath(QStringLiteral("translations"));
        for (const QString& name : {QStringLiteral("mmc_pt_BR.qm"),
                                    QStringLiteral("index_v2.json")}) {
            QFile source(QStringLiteral("assets:/translations/") + name);
            if (!source.open(QIODevice::ReadOnly)) {
                qWarning() << "PineconeMC Android: missing bundled pt_BR asset" << name;
                continue;
            }
            const QByteArray content = source.readAll();
            const QString destination = QStringLiteral("translations/") + name;
            QFile installed(destination);
            if (installed.open(QIODevice::ReadOnly) && installed.readAll() == content)
                continue;
            QSaveFile target(destination);
            if (!target.open(QIODevice::WriteOnly) ||
                target.write(content) != content.size() || !target.commit()) {
                qWarning() << "PineconeMC Android: cannot write pt_BR translation" << destination;
            }
        }
        // Existing test APKs saved en_US when it was the only available row.
        const QString saved = settings()->get("Language").toString();
        if (saved.isEmpty() || saved == QStringLiteral("en_US"))
            settings()->set("Language", QStringLiteral("pt_BR"));
#endif
        m_translations.reset(new TranslationsModel("translations"));
#ifdef Q_OS_ANDROID
        if (!m_translations->selectLanguage(settings()->get("Language").toString()))
            qWarning() << "PineconeMC Android: pt_BR catalog not yet loaded";
        else
            qInfo() << "PineconeMC Android: built-in Brazilian Portuguese catalog active";
#endif''')

# Fix the original desktop toolbar disappearing in Android: a desktop setting
# ("MenuBarInsteadOfToolBar") hides the only Add Instance action, while Qt's
# mobile activity does not expose the desktop menu bar.
patch("launcher/ui/MainWindow.cpp",
      '''    ui->menuBar->setVisible(APPLICATION->settings()->get("MenuBarInsteadOfToolBar").toBool());
    ui->mainToolBar->setVisible(ui->menuBar->isNativeMenuBar() || !APPLICATION->settings()->get("MenuBarInsteadOfToolBar").toBool());
    ui->actionCAT->setVisible(APPLICATION->settings()->get("CatButtonVisible").toBool());''',
      '''#ifdef Q_OS_ANDROID
    ui->menuBar->setVisible(false);
    ui->mainToolBar->setVisible(false);
    ui->mainToolBar->setMovable(false);
    ui->mainToolBar->setFloatable(false);
    ui->mainToolBar->setIconSize(QSize(22, 22));
    ui->mainToolBar->setToolButtonStyle(Qt::ToolButtonTextBesideIcon);
    ui->mainToolBar->setMinimumHeight(0);
    ui->instanceToolBar->setVisible(false);
    ui->newsToolBar->setVisible(false);
    ui->statusBar->setVisible(false);
    // Keep touch-sized original actions; they trigger the REAL C++ handlers.
    ui->actionAddInstance->setText(QStringLiteral("Adicionar instância"));
    ui->actionSettings->setText(QStringLiteral("Configurações"));
    ui->actionFoldersButton->setText(QStringLiteral("Pastas"));
    ui->actionAccountsButton->setText(QStringLiteral("Contas"));
    ui->actionHelpButton->setText(QStringLiteral("Ajuda"));
    for (QAction* action : ui->mainToolBar->actions()) {
        if (auto* control = qobject_cast<QToolButton*>(ui->mainToolBar->widgetForAction(action)))
            control->setMinimumHeight(42);
    }
    ui->actionCAT->setVisible(false);
#else
    ui->menuBar->setVisible(APPLICATION->settings()->get("MenuBarInsteadOfToolBar").toBool());
    ui->mainToolBar->setVisible(ui->menuBar->isNativeMenuBar() || !APPLICATION->settings()->get("MenuBarInsteadOfToolBar").toBool());
    ui->actionCAT->setVisible(APPLICATION->settings()->get("CatButtonVisible").toBool());
#endif''')

# On Qt Android, QMainWindow::restoreState() runs AFTER MainWindow's
# constructor. It may re-hide the main toolbar regardless of the earlier
# visibility fix. Restore it after the saved desktop state is applied.
patch("launcher/Application.cpp",
      '''        m_mainWindow->restoreState(QByteArray::fromBase64(APPLICATION->settings()->get("MainWindowState").toString().toUtf8()));''',
      '''        m_mainWindow->restoreState(QByteArray::fromBase64(APPLICATION->settings()->get("MainWindowState").toString().toUtf8()));
#ifdef Q_OS_ANDROID
        // Desktop window-state snapshots can hide the action toolbar on a
        // phone, and Qt Android doesn't expose desktop menu-bar controls.
        if (auto* toolbar = m_mainWindow->findChild<QToolBar*>(QStringLiteral("mainToolBar"))) {
            toolbar->hide();
        }
#endif''')
patch("launcher/Application.cpp",
      '#include <QWindow>',
      '''#include <QWindow>
#ifdef Q_OS_ANDROID
#include <QToolBar>
#endif''')

# Create a touch-sized rail INSIDE the actual central widget. It is not a
# QMainWindow toolbar, so Android's saved window state cannot hide it.
# The buttons call the original C++ handlers; no fake launcher or web UI.
patch("launcher/ui/MainWindow.cpp",
      '#include <QToolButton>',
      '''#include <QToolButton>
#ifdef Q_OS_ANDROID
#include <QVBoxLayout>
#include <QPushButton>
#endif''')
patch("launcher/ui/MainWindow.cpp",
      '''        ui->horizontalLayout->addWidget(view);
    }''',
      '''#ifdef Q_OS_ANDROID
        // Respect the native Android top title inset for the instance grid,
        // not just the left controls. Otherwise the first instance is hidden.
        auto* instancePanel = new QWidget(ui->centralWidget);
        auto* instanceLayout = new QVBoxLayout(instancePanel);
        instanceLayout->setContentsMargins(0, 0, 0, 0);
        instanceLayout->setSpacing(0);
        instanceLayout->addWidget(view);
        ui->horizontalLayout->addWidget(instancePanel, 1);
#else
        ui->horizontalLayout->addWidget(view);
#endif
#ifdef Q_OS_ANDROID
        // QHBoxLayout already belongs to the original central widget.
        // Inserting at index zero creates a persistent left control rail
        // without replacing the original instance list or changing its model.
        auto* mobileActionRail = new QWidget(ui->centralWidget);
        mobileActionRail->setObjectName(QStringLiteral("mobileActionRail"));
        mobileActionRail->setFixedWidth(146);
        mobileActionRail->setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Expanding);
        auto* mobileActions = new QVBoxLayout(mobileActionRail);
        // Qt for Android reserves a native title/status inset above the Qt
        // content; keep the FIRST action below that area.
        mobileActions->setContentsMargins(6, 6, 6, 6);
        mobileActions->setSpacing(6);
        auto* addInstance = new QPushButton(QStringLiteral("+ Instância"), mobileActionRail);
        addInstance->setObjectName(QStringLiteral("androidAddInstance"));
        addInstance->setMinimumHeight(46);
        addInstance->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
        addInstance->setToolTip(QStringLiteral("Criar uma instância do Minecraft Java"));
        mobileActions->addWidget(addInstance);
        connect(addInstance, &QPushButton::clicked, this,
                &MainWindow::on_actionAddInstance_triggered);
        // Real game launch remains disabled until an instance is selected;
        // mirror the upstream QAction state rather than bypassing checks.
        auto* playButton = new QPushButton(QStringLiteral("Jogar"), mobileActionRail);
        playButton->setObjectName(QStringLiteral("androidLaunchInstance"));
        playButton->setMinimumHeight(46);
        playButton->setEnabled(ui->actionLaunchInstance->isEnabled());
        mobileActions->addWidget(playButton);
        connect(playButton, &QPushButton::clicked, this,
                &MainWindow::on_actionLaunchInstance_triggered);
        connect(ui->actionLaunchInstance, &QAction::changed, playButton,
                [this, playButton]() {
                    playButton->setEnabled(ui->actionLaunchInstance->isEnabled());
                });
        auto* accountButton = new QPushButton(QStringLiteral("Contas"), mobileActionRail);
        accountButton->setMinimumHeight(46);
        mobileActions->addWidget(accountButton);
        connect(accountButton, &QPushButton::clicked, this,
                &MainWindow::on_actionManageAccounts_triggered);
        auto* settingsButton = new QPushButton(QStringLiteral("Configurações"), mobileActionRail);
        settingsButton->setMinimumHeight(46);
        mobileActions->addWidget(settingsButton);
        connect(settingsButton, &QPushButton::clicked, this,
                &MainWindow::on_actionSettings_triggered);
        mobileActions->addStretch();
        ui->horizontalLayout->insertWidget(0, mobileActionRail);
        qInfo() << "PineconeMC Android: central mobile action rail enabled";
#endif
    }''')

# Make original empty-state instructions explicitly readable on Android,
# regardless of whether the upstream Prism translation covers them.
patch("launcher/ui/instanceview/InstanceView.cpp",
      '        QString emptyString = tr("Welcome!") + "\\n" + tr("Click \\"Add Instance\\" to get started.");',
      '''#ifdef Q_OS_ANDROID
        QString emptyString = QStringLiteral("Bem-vindo!\\nToque em Adicionar instância para começar.");
#else
        QString emptyString = tr("Welcome!") + "\\n" + tr("Click \\"Add Instance\\" to get started.");
#endif''')

# The native Pinecone site may respond to HEAD requests while its metadata
# endpoint is blocked on Android carriers. Pin the upstream project's OWN
# official GitHub Pages mirror, whose net.minecraft index is available and
# updated, instead of showing an empty vanilla version list. Keep the choice
# in Settings so users can change the mirror.
patch("launcher/Application.cpp",
      '    bool languageRequired = settings()->get("Language").toString().isEmpty();',
      '''#ifdef Q_OS_ANDROID
    const QString oldMeta = settings()->get("MetaURLOverride").toString().trimmed();
    if (oldMeta.isEmpty() ||
        oldMeta.startsWith(QStringLiteral("https://meta.pineconemc.ru/")) ||
        oldMeta.startsWith(QStringLiteral("https://pineconemc.github.io/"))) {
        settings()->set("MetaURLOverride",
                        QStringLiteral("https://elyprismlauncher.github.io/meta/v1/"));
        qInfo() << "PineconeMC Android: official GitHub metadata mirror selected";
    }
    // Prevent a successful HEAD to a different host from overwriting the
    // selected metadata endpoint with a URL that fails on the phone.
    settings()->set("PineconeAutoServers", false);
#endif
    bool languageRequired = settings()->get("Language").toString().isEmpty();''')

# Keep the upstream instance-form hierarchy intact on Android. The previous
# attempt moved its QGridLayout and nested PageContainer into another scroll
# area and placed duplicate action buttons at the top; this broke the page
# viewport, obscured the name/group inputs and confused touch navigation.
# The original PageContainer already scrolls the active page. Keep its real
# OK/Cancel/Help QDialogButtonBox at the BOTTOM and never reparent its layout.
patch("launcher/ui/dialogs/NewInstanceDialog.cpp",
      '#include <QScreen>',
      '''#include <QScreen>
#ifdef Q_OS_ANDROID
#include <QGuiApplication>
#endif''')
patch("launcher/ui/dialogs/NewInstanceDialog.cpp",
      '''    if (APPLICATION->settings()->get("NewInstanceGeometry").isValid()) {
        restoreGeometry(QByteArray::fromBase64(APPLICATION->settings()->get("NewInstanceGeometry").toString().toUtf8()));
    } else {
        auto screen = parent->screen();
        auto geometry = screen->availableSize();
        resize(width(), qMin(geometry.height() - 50, 710));
    }''',
      '''#ifdef Q_OS_ANDROID
    // Original header, page stack and footer remain in one QVBoxLayout.
    // No duplicated top buttons; original QDialogButtonBox stays at bottom.
    ui->verticalLayout->setContentsMargins(7, 6, 7, 7);
    ui->verticalLayout->setSpacing(2);
    ui->iconButton->setIconSize(QSize(40, 40));
    ui->iconButton->setMaximumSize(QSize(48, 48));
    m_container->setMinimumSize(0, 0);
    m_container->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    auto* originalOk = m_buttons->button(QDialogButtonBox::Ok);
    auto* originalCancel = m_buttons->button(QDialogButtonBox::Cancel);
    originalOk->setText(QStringLiteral("Criar instância"));
    originalCancel->setText(QStringLiteral("Cancelar"));
    originalOk->setMinimumHeight(46);
    originalCancel->setMinimumHeight(46);
    m_buttons->setMinimumHeight(52);
    setMinimumSize(0, 0);
    // Android's window manager assigns the actual available geometry;
    // never restore the saved desktop dialog size.
    const QScreen* display = parent ? parent->screen() : QGuiApplication::primaryScreen();
    if (display) {
        const QSize size = display->availableGeometry().size();
        setMaximumSize(size);
        resize(size);
    }
    qInfo() << "PineconeMC Android: original instance form with bottom actions";
#else
    if (APPLICATION->settings()->get("NewInstanceGeometry").isValid()) {
        restoreGeometry(QByteArray::fromBase64(APPLICATION->settings()->get("NewInstanceGeometry").toString().toUtf8()));
    } else {
        auto screen = parent->screen();
        auto geometry = screen->availableSize();
        resize(width(), qMin(geometry.height() - 50, 710));
    }
#endif''')

# Android already provides an offline pt-BR catalog and picks a valid dark
# theme/icon. Do not force the PC-only Appearance step on every fresh install:
# the real launcher remains configurable later under Configurações.
patch("launcher/Application.cpp",
      '''    bool wizardRequired = javaRequired || languageRequired || pasteInterventionRequired || themeInterventionRequired || askjava || login;''',
      '''#ifdef Q_OS_ANDROID
    if (!validIcons)
        settings()->set("IconTheme", QStringLiteral("pe_colored"));
    if (!validWidgets)
        settings()->set("ApplicationTheme", QStringLiteral("system"));
    themeInterventionRequired = false;
    qInfo() << "PineconeMC Android: desktop-only Appearance setup disabled";
#endif
    bool wizardRequired = javaRequired || languageRequired || pasteInterventionRequired || themeInterventionRequired || askjava || login;''')

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
        // Leave generous margin for Android's gesture bar and insets.
        const int height = qMax(230, screenSize.height() - 96);
        setMaximumSize(width, height);
        resize(qMin(620, width), qMin(660, height));
        qInfo() << "PineconeMC Android wizard size" << size()
                << "available landscape area" << screenSize;
    });
#else
    resize(620, 660);
    setMinimumSize(300, 400);
#endif''')

# Make the language list compact on phones. The desktop QTreeView used almost
# all of the short landscape screen for a single English row.
patch("launcher/ui/widgets/LanguageSelectionWidget.cpp",
      '    languageView->setRootIsDecorated(false);',
      '''    languageView->setRootIsDecorated(false);
#ifdef Q_OS_ANDROID
    // Keep the original language model and scrolling; leave room for actions.
    languageView->setMinimumHeight(65);
    languageView->setMaximumHeight(160);
#endif''')

# Keep working navigation at the TOP of every original wizard page, not below
# the Android navigation bar. These buttons invoke Qt's actual Next/Back/Finish
# buttons, preserving upstream validation and settings handling.
patch("launcher/ui/setupwizard/SetupWizard.cpp",
      '#include <QAbstractButton>',
      '''#include <QAbstractButton>
#ifdef Q_OS_ANDROID
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPushButton>
#endif''')
patch("launcher/ui/setupwizard/SetupWizard.cpp",
      '''    auto basePagePtr = getBasePage(id);
    if (!basePagePtr) {
        return;
    }''',
      '''    auto basePagePtr = getBasePage(id);
    if (!basePagePtr) {
        return;
    }
#ifdef Q_OS_ANDROID
    // In a phone's landscape viewport, the desktop QWizard footer can be
    // below the actual touchscreen. Add native-sized controls to the top of
    // each original page instead of replacing the wizard or skipping steps.
    if (auto* pageLayout = qobject_cast<QVBoxLayout*>(basePagePtr->layout())) {
        if (!basePagePtr->findChild<QWidget*>(
                QStringLiteral("androidWizardNavigation"),
                Qt::FindDirectChildrenOnly)) {
            auto* toolbar = new QWidget(basePagePtr);
            toolbar->setObjectName(QStringLiteral("androidWizardNavigation"));
            auto* row = new QHBoxLayout(toolbar);
            row->setContentsMargins(0, 2, 0, 8);
            row->setSpacing(12);
            auto* backButton = new QPushButton(tr("Voltar"), toolbar);
            auto* forwardButton = new QPushButton(tr("Avançar"), toolbar);
            backButton->setMinimumHeight(48);
            forwardButton->setMinimumHeight(48);
            backButton->setMinimumWidth(120);
            forwardButton->setMinimumWidth(140);
            backButton->setEnabled(visitedIds().size() > 1);
            forwardButton->setText(basePagePtr->isFinalPage() ?
                                   tr("Concluir") : tr("Próximo"));
            row->addWidget(backButton);
            row->addStretch();
            row->addWidget(forwardButton);
            connect(backButton, &QPushButton::clicked, this, [this]() {
                auto* original = button(QWizard::BackButton);
                if (original && original->isEnabled())
                    original->click();
            });
            connect(forwardButton, &QPushButton::clicked, this, [this]() {
                auto* page = currentPage();
                auto* original = button(page && page->isFinalPage() ?
                                        QWizard::FinishButton : QWizard::NextButton);
                if (original && original->isEnabled())
                    original->click();
            });
            pageLayout->insertWidget(0, toolbar);
            qInfo() << "PineconeMC Android: visible upper navigation on page" << id;
        }
    }
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

# The Android activity now uses a no-title fullscreen theme; show the
# original Qt main window fullscreen as well. Never restore a desktop window
# rectangle as the phone viewport: it clips the instance list and menus.
patch("launcher/Application.cpp",
      '''        m_mainWindow->restoreGeometry(QByteArray::fromBase64(APPLICATION->settings()->get("MainWindowGeometry").toString().toUtf8()));''',
      '''#ifndef Q_OS_ANDROID
        m_mainWindow->restoreGeometry(QByteArray::fromBase64(APPLICATION->settings()->get("MainWindowGeometry").toString().toUtf8()));
#endif''')
patch("launcher/Application.cpp",
      '''        } else {
            m_mainWindow->show();
        }

        m_mainWindow->checkInstancePathForProblems();''',
      '''        } else {
#ifdef Q_OS_ANDROID
            m_mainWindow->showFullScreen();
#else
            m_mainWindow->show();
#endif
        }

        m_mainWindow->checkInstancePathForProblems();''')

# Native dialogs must fit the current Android viewport, rather than desktop
# geometry saved on a previous run. This makes settings/other pages readable.
patch("launcher/ui/pagedialog/PageDialog.cpp",
      '#include <QVBoxLayout>',
      '''#include <QVBoxLayout>
#ifdef Q_OS_ANDROID
#include <QScreen>
#include <QGuiApplication>
#endif''')
patch("launcher/ui/pagedialog/PageDialog.cpp",
      '''    restoreGeometry(QByteArray::fromBase64(APPLICATION->settings()->get("PagedGeometry").toString().toUtf8()));''',
      '''#ifdef Q_OS_ANDROID
    setWindowFlag(Qt::FramelessWindowHint, true);
    setMinimumSize(0, 0);
    const QScreen* mobileScreen = parent ? parent->screen() : QGuiApplication::primaryScreen();
    if (mobileScreen) {
        const QSize available = mobileScreen->availableGeometry().size();
        setMaximumSize(available);
        resize(available);
    }
    setWindowState(windowState() | Qt::WindowFullScreen);
#else
    restoreGeometry(QByteArray::fromBase64(APPLICATION->settings()->get("PagedGeometry").toString().toUtf8()));
#endif''')

# The settings pages have desktop minimum widths and heights. Use a real
# QScrollArea for the original QStackedLayout, not a clipped view or a fake
# replacement page. Restrict the sidebar and let the active page scroll.
patch("launcher/ui/widgets/PageContainer.cpp",
      '#include <QSortFilterProxyModel>',
      '''#include <QSortFilterProxyModel>
#ifdef Q_OS_ANDROID
#include <QScrollArea>
#endif''')
patch("launcher/ui/widgets/PageContainer.cpp",
      '''    m_layout->addLayout(m_pageStack, 1, 1, 1, 1);
    m_layout->setColumnStretch(1, 4);''',
      '''#ifdef Q_OS_ANDROID
    auto* activePageHost = new QWidget(this);
    activePageHost->setLayout(m_pageStack);
    auto* mobileScroll = new QScrollArea(this);
    mobileScroll->setObjectName(QStringLiteral("androidSettingsScroll"));
    mobileScroll->setWidgetResizable(true);
    mobileScroll->setFrameShape(QFrame::NoFrame);
    mobileScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAsNeeded);
    mobileScroll->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);
    mobileScroll->setWidget(activePageHost);
    m_layout->addWidget(mobileScroll, 1, 1, 1, 1);
    m_pageList->setMinimumWidth(0);
    m_pageList->setMaximumWidth(152);
    m_pageList->setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Expanding);
    m_layout->setColumnStretch(0, 0);
#else
    m_layout->addLayout(m_pageStack, 1, 1, 1, 1);
#endif
    m_layout->setColumnStretch(1, 4);''')

# Fullscreen mobile dialog retains the real bottom buttons, with no extra
# headers or nested reparented scrolling containers.
patch("launcher/ui/dialogs/NewInstanceDialog.cpp",
      '''    qInfo() << "PineconeMC Android: original instance form with bottom actions";''',
      '''    setWindowFlag(Qt::FramelessWindowHint, true);
    setWindowState(windowState() | Qt::WindowFullScreen);
    qInfo() << "PineconeMC Android: fullscreen original instance form";''')

# The original empty-state overlay is sized for desktop. Reduce its text and
# make it explicit that an instance must be created before anything can appear.
patch("launcher/ui/instanceview/InstanceView.cpp",
      '''        QFont font("sans", 20);
        font.setBold(true);''',
      '''#ifdef Q_OS_ANDROID
        QFont font("sans", 12);
#else
        QFont font("sans", 20);
#endif
        font.setBold(true);''')
patch("launcher/ui/instanceview/InstanceView.cpp",
      '''QStringLiteral("Bem-vindo!\\nToque em Adicionar instância para começar.");''',
      '''QStringLiteral("Sem instâncias.\\nToque em + Instância para criar uma.");''')

print("Android CMake adjustments applied to actual PineconeMC source.")
