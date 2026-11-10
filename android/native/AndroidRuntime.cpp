// SPDX-License-Identifier: GPL-3.0-only
// Android runtime diagnostics for the original PineconeMC.
#include "AndroidRuntime.h"
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QJniObject>
#include <QStandardPaths>

namespace AndroidRuntime {
Status inspect()
{
    Status result;
    result.runtimeVersion = 17;

    const QJniObject context = QNativeInterface::QAndroidApplication::context();
    if (!context.isValid()) {
        result.error = QStringLiteral("O Android não disponibilizou o contexto do aplicativo.");
        return result;
    }
    const QJniObject info =
        context.callObjectMethod("getApplicationInfo", "()Landroid/content/pm/ApplicationInfo;");
    if (!info.isValid()) {
        result.error = QStringLiteral("Não foi possível consultar os arquivos nativos do Android.");
        return result;
    }
    result.nativeLibraryDirectory =
        info.getObjectField("nativeLibraryDir", "Ljava/lang/String;").toString();

    // Android 10+ forbids execve() of binaries unpacked into writable app data.
    // Executable machine code must be shipped as part of the signed APK.
    if (result.nativeLibraryDirectory.isEmpty()) {
        result.error = QStringLiteral("A pasta de bibliotecas nativas não foi encontrada.");
        return result;
    }
    const QDir libs(result.nativeLibraryDirectory);
    result.javaExecutable = libs.filePath(QStringLiteral("libpinecone_java.so"));
    result.jvmLibrary = libs.filePath(QStringLiteral("libjvm.so"));
    result.runtimeModules = QDir(
        QStandardPaths::writableLocation(QStandardPaths::AppDataLocation))
        .filePath(QStringLiteral("runtime/java-17/lib/modules"));

    if (!QFileInfo(result.javaExecutable).isExecutable()) {
        result.error = QStringLiteral(
            "O executável Java 17 para Android ARM64 ainda não está incluído no APK. "
            "É necessário compilar e empacotar o runtime OpenJDK para Android.");
    } else if (!QFileInfo(result.jvmLibrary).isFile()) {
        result.error = QStringLiteral(
            "A biblioteca OpenJDK libjvm.so para Android ARM64 não está instalada.");
    } else if (!QFileInfo(result.runtimeModules).isFile()) {
        result.error = QStringLiteral(
            "Os módulos Java SE 17 não foram instalados no armazenamento do aplicativo.");
    }
    return result;
}
} // namespace AndroidRuntime
