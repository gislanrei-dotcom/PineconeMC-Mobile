// SPDX-License-Identifier: GPL-3.0-only
// Android runtime diagnostics for the original PineconeMC.
#include "AndroidRuntime.h"
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QJniObject>
#include <QStandardPaths>
#include <QCryptographicHash>
#include <QFile>
#include <QSaveFile>
#include <QStringList>

namespace AndroidRuntime {
namespace {

// The runtime manifest contains only app-owned relative paths, never URLs or
// absolute paths. It is generated alongside the corresponding APK assets.
bool safeRelativePath(const QString& path)
{
    if (path.isEmpty() || path.startsWith('/') || path.contains('\\'))
        return false;
    if (QDir::cleanPath(path) != path)
        return false;
    for (const QString& component : path.split('/')) {
        if (component.isEmpty() || component == "." || component == "..")
            return false;
    }
    return true;
}

QByteArray hashFile(const QString& path)
{
    QFile input(path);
    if (!input.open(QIODevice::ReadOnly))
        return {};
    QCryptographicHash sha(QCryptographicHash::Sha256);
    if (!sha.addData(&input))
        return {};
    return sha.result().toHex();
}

// Copies non-executable Java SE data to private storage, and links any Java
// .so files to nativeLibraryDir. Android's app-data executable restriction
// means native machine code is NEVER unpacked as ordinary writable assets.
QString installRuntimeAssets(const QString& nativeDir, const QString& javaHome, int major)
{
    const QString assetPrefix = QStringLiteral("assets:/runtime/java-%1/").arg(major);
    QFile manifest(assetPrefix + QStringLiteral("manifest.tsv"));
    if (!manifest.exists())
        return QStringLiteral("Java %1 não está incluído neste APK.").arg(major);
    if (!manifest.open(QIODevice::ReadOnly))
        return QStringLiteral("Não foi possível abrir o manifesto do Java Android.");

    while (!manifest.atEnd()) {
        const QString line = QString::fromUtf8(manifest.readLine()).trimmed();
        if (line.isEmpty() || line.startsWith('#'))
            continue;
        const QStringList parts = line.split('\t');
        if (parts.size() < 3 || !safeRelativePath(parts.at(1)))
            return QStringLiteral("Manifesto Java Android inválido: caminho relativo incorreto.");
        const QString destination = QDir(javaHome).filePath(parts.at(1));
        if (!QDir().mkpath(QFileInfo(destination).absolutePath()))
            return QStringLiteral("Não foi possível preparar a pasta do Java Android.");

        if (parts.at(0) == "F" && parts.size() == 4) {
            bool validSize = false;
            const qint64 expectedSize = parts.at(2).toLongLong(&validSize);
            const QByteArray expectedHash = parts.at(3).toLatin1();
            if (!validSize || expectedSize < 0 || expectedHash.size() != 64)
                return QStringLiteral("Manifesto Java Android contém tamanho ou SHA256 inválido.");
            QFileInfo existing(destination);
            if (existing.isFile() && existing.size() == expectedSize
                && hashFile(destination) == expectedHash) {
                continue;
            }

            QFile asset(assetPrefix + parts.at(1));
            if (!asset.open(QIODevice::ReadOnly))
                return QStringLiteral("Arquivo Java Android ausente do APK: ") + parts.at(1);
            QSaveFile output(destination);
            if (!output.open(QIODevice::WriteOnly))
                return QStringLiteral("Não foi possível criar arquivo Java Android: ") + parts.at(1);
            QCryptographicHash sha(QCryptographicHash::Sha256);
            qint64 written = 0;
            while (!asset.atEnd()) {
                const QByteArray block = asset.read(128 * 1024);
                if (block.isEmpty() && asset.error() != QFileDevice::NoError)
                    return QStringLiteral("Falha ao ler arquivo Java Android: ") + parts.at(1);
                if (output.write(block) != block.size())
                    return QStringLiteral("Sem espaço ou falha ao gravar Java Android: ") + parts.at(1);
                sha.addData(block);
                written += block.size();
            }
            if (written != expectedSize || sha.result().toHex() != expectedHash)
                return QStringLiteral("Falha de integridade SHA256 do Java Android: ") + parts.at(1);
            if (!output.commit())
                return QStringLiteral("Falha ao salvar arquivo Java Android: ") + parts.at(1);
        } else if (parts.at(0) == "L" && parts.size() == 3) {
            const QString library = parts.at(2);
            if (!library.startsWith("lib") || !library.endsWith(".so")
                || library.contains('/') || library.contains('\\')) {
                return QStringLiteral("Manifesto Java Android contém nome de biblioteca inválido.");
            }
            const QString nativePath = QDir(nativeDir).filePath(library);
            if (!QFileInfo(nativePath).isFile())
                return QStringLiteral("Biblioteca Java Android não incluída no APK: ") + library;
            if (QFileInfo(destination).canonicalFilePath() == QFileInfo(nativePath).canonicalFilePath())
                continue;
            QFile::remove(destination);
            if (!QFile::link(nativePath, destination))
                return QStringLiteral("Não foi possível vincular biblioteca Java Android: ") + library;
        } else {
            return QStringLiteral("Manifesto Java Android contém registro inválido.");
        }
    }
    return {};
}

} // namespace

Status inspect(int requiredMajor)
{
    Status result;
    result.runtimeVersion = requiredMajor;
    if (requiredMajor != 8 && requiredMajor != 17) {
        result.error = QStringLiteral("Runtime Java %1 ainda não empacotado para Android.").arg(requiredMajor);
        return result;
    }

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
    result.jvmLibrary = libs.filePath(requiredMajor == 8
        ? QStringLiteral("libp8_jvm.so") : QStringLiteral("libjvm.so"));
    const QString javaHome = QDir(
        QStandardPaths::writableLocation(QStandardPaths::AppDataLocation))
       .filePath(QStringLiteral("runtime/java-%1").arg(requiredMajor));
    result.runtimeModules = QDir(javaHome).filePath(requiredMajor == 8
        ? QStringLiteral("lib/rt.jar") : QStringLiteral("lib/modules"));
    const QString installError = installRuntimeAssets(result.nativeLibraryDirectory, javaHome, requiredMajor);
    if (!installError.isEmpty()) {
        result.error = installError;
        return result;
    }

    if (!QFileInfo(result.javaExecutable).isExecutable()) {
        result.error = QStringLiteral(
            "O executável Java Android para Android ARM64 ainda não está incluído no APK. "
            "É necessário compilar e empacotar o runtime OpenJDK para Android.");
    } else if (!QFileInfo(result.jvmLibrary).isFile()) {
        result.error = QStringLiteral(
            "A biblioteca nativa OpenJDK exigida não está instalada.");
    } else if (!QFileInfo(result.runtimeModules).isFile()) {
        result.error = QStringLiteral(
            "A biblioteca de classes Java exigida não foi instalada no armazenamento do aplicativo.");
    }
    return result;
}
} // namespace AndroidRuntime
