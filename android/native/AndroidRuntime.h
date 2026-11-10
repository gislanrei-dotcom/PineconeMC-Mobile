// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <QString>
namespace AndroidRuntime {
struct Status {
    int runtimeVersion = 0;
    QString nativeLibraryDirectory;
    QString javaExecutable;
    QString jvmLibrary;
    QString runtimeModules;
    QString error;
    bool available() const { return error.isEmpty(); }
};
Status inspect();
} // namespace AndroidRuntime
