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
// Version-specific Android OpenJDK images (8 for classic MC, 17 for newer).
Status inspect(int requiredMajor = 17);
} // namespace AndroidRuntime
