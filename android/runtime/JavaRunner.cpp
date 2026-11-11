// SPDX-License-Identifier: GPL-3.0-only
// Experimental PineconeMC Android Java SE subprocess launcher.
// This is an independent JNI invocation adapter, NOT a fork of any Android launcher.
// It must run as its own APK-packaged native executable, not in Android ART's VM.
#include <jni.h>
#include <dlfcn.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

namespace {
using CreateJavaVM = jint (*)(JavaVM**, void**, void*);

bool starts(const std::string& text, const char* prefix)
{
    return text.rfind(prefix, 0) == 0;
}

int usageError(const char* message)
{
    std::fprintf(stderr, "PineconeMC Java runtime: %s\n", message);
    return 64;
}

std::string javaLibraryPath(const char* executable)
{
    if (const char* configured = std::getenv("PINECONE_JVM_LIBRARY"); configured && *configured)
        return configured;
    std::string path = executable ? executable : "";
    const auto end = path.find_last_of('/');
    if (end == std::string::npos)
        return "libjvm.so";
    return path.substr(0, end + 1) + "libjvm.so";
}

// JNI expects UTF-16 here; NewStringUTF would expect modified UTF-8,
// which differs from ordinary UTF-8 for supplementary Unicode characters.
std::u16string fromUtf8(const std::string& bytes)
{
    std::u16string out;
    for (size_t i = 0; i < bytes.size();) {
        const auto lead = static_cast<unsigned char>(bytes[i]);
        char32_t code = 0;
        size_t count = 0;
        if (lead < 0x80) { code = lead; count = 1; }
        else if (lead >= 0xC2 && lead <= 0xDF) { code = lead & 0x1F; count = 2; }
        else if (lead >= 0xE0 && lead <= 0xEF) { code = lead & 0x0F; count = 3; }
        else if (lead >= 0xF0 && lead <= 0xF4) { code = lead & 0x07; count = 4; }
        bool valid = count && i + count <= bytes.size();
        if (valid) {
            for (size_t j = 1; j < count; ++j) {
                const auto part = static_cast<unsigned char>(bytes[i + j]);
                if ((part & 0xC0) != 0x80) { valid = false; break; }
                code = (code << 6) | (part & 0x3F);
            }
        }
        if (valid && ((count == 2 && code < 0x80) ||
                      (count == 3 && code < 0x800) ||
                      (count == 4 && code < 0x10000) ||
                      (code >= 0xD800 && code <= 0xDFFF) || code > 0x10FFFF))
            valid = false;
        if (!valid) { out.push_back(0xFFFD); ++i; continue; }
        i += count;
        if (code <= 0xFFFF) {
            out.push_back(static_cast<char16_t>(code));
        } else {
            code -= 0x10000;
            out.push_back(static_cast<char16_t>(0xD800 + (code >> 10)));
            out.push_back(static_cast<char16_t>(0xDC00 + (code & 0x3FF)));
        }
    }
    return out;
}

} // namespace

int main(int argc, char** argv)
{
    if (argc < 2)
        return usageError("faltaram argumentos da JVM ou a classe Java de entrada");

    std::vector<std::string> vmStrings;
    std::vector<std::string> appArgs;
    std::string mainClass;
    int next = 1;

    for (; next < argc; ++next) {
        std::string arg(argv[next]);
        if (arg == "-cp" || arg == "-classpath" || arg == "--class-path") {
            if (next + 1 >= argc)
                return usageError("-cp precisa de uma lista de arquivos");
            vmStrings.push_back(std::string("-Djava.class.path=") + argv[++next]);
        } else if (arg == "-jar") {
            if (next + 1 >= argc)
                return usageError("-jar precisa do caminho de um arquivo");
            const std::string jar(argv[++next]);
            // PineconeMC's own Java version checker has a known main class.
            // Other -jar invocations need a JAR manifest reader before support.
            if (jar.size() < 13 || jar.substr(jar.size() - 13) != "JavaCheck.jar")
                return usageError("-jar não suportado nesta etapa, exceto JavaCheck.jar");
            vmStrings.push_back("-Djava.class.path=" + jar);
            mainClass = "JavaCheck";
            ++next;
            break;
        } else if (arg == "--add-opens" || arg == "--add-exports" ||
                   arg == "--add-reads" || arg == "--add-modules" ||
                   arg == "--module-path" || arg == "--patch-module") {
            if (next + 1 >= argc)
                return usageError("opção modular precisa de um valor");
            vmStrings.push_back(arg + "=" + argv[++next]);
        } else if (arg == "--enable-preview" || arg == "-ea" || arg == "-esa" ||
                   starts(arg, "-D") || starts(arg, "-X") || starts(arg, "-XX:") ||
                   starts(arg, "--add-") || starts(arg, "--module-") ||
                   starts(arg, "--enable-")) {
            vmStrings.push_back(arg);
        } else if (!arg.empty() && arg[0] == '-') {
            return usageError("opção de JVM ainda não reconhecida");
        } else {
            mainClass = arg;
            ++next;
            break;
        }
    }
    if (mainClass.empty())
        return usageError("a classe Java de entrada não foi informada");
    for (; next < argc; ++next)
        appArgs.emplace_back(argv[next]);

    // Point the future Android/Bionic JVM at the Java SE module image and
    // preserve Minecraft's instance-native library path.
    if (const char* javaHome = std::getenv("PINECONE_JAVA_HOME"); javaHome && *javaHome) {
        vmStrings.emplace_back(std::string("-Djava.home=") + javaHome);
    }
    if (const char* nativeDirectory = std::getenv("PINECONE_NATIVE_LIB_DIR");
        nativeDirectory && *nativeDirectory) {
        const std::string prefix = "-Djava.library.path=";
        bool merged = false;
        for (auto& option : vmStrings) {
            if (starts(option, prefix.c_str())) {
                option = prefix + nativeDirectory + ":" + option.substr(prefix.size());
                merged = true;
            }
        }
        if (!merged)
            vmStrings.emplace_back(prefix + nativeDirectory);
    }

    const std::string jvmPath = javaLibraryPath(argv[0]);
    void* library = dlopen(jvmPath.c_str(), RTLD_NOW | RTLD_GLOBAL);
    if (!library) {
        std::fprintf(stderr, "OpenJDK não encontrado em %s: %s\n",
                     jvmPath.c_str(), dlerror());
        return 70;
    }
    auto create = reinterpret_cast<CreateJavaVM>(dlsym(library, "JNI_CreateJavaVM"));
    if (!create) {
        std::fprintf(stderr, "libjvm.so não exporta JNI_CreateJavaVM\n");
        dlclose(library);
        return 71;
    }

    std::vector<JavaVMOption> vmOptions;
    vmOptions.reserve(vmStrings.size());
    for (std::string& option : vmStrings)
        vmOptions.push_back({const_cast<char*>(option.c_str()), nullptr});

    JavaVMInitArgs args{};
    // Android NDK's jni.h does not declare JNI_VERSION_1_8. This process
    // creates its own Java SE JVM through the Invocation API, not Android ART.
    // The JNI 1.8 numeric version is 0x00010008 on both host and Android.
    args.version = static_cast<jint>(0x00010008);
    args.nOptions = static_cast<jint>(vmOptions.size());
    args.options = vmOptions.data();
    args.ignoreUnrecognized = JNI_FALSE;
    JavaVM* vm = nullptr;
    JNIEnv* env = nullptr;
    const jint code = create(&vm, reinterpret_cast<void**>(&env), &args);
    if (code != JNI_OK || !env || !vm) {
        std::fprintf(stderr, "OpenJDK não iniciou: JNI_CreateJavaVM retornou %d\n", code);
        dlclose(library);
        return 72;
    }

    std::replace(mainClass.begin(), mainClass.end(), '.', '/');
    jclass entry = env->FindClass(mainClass.c_str());
    if (!entry || env->ExceptionCheck()) {
        env->ExceptionDescribe();
        vm->DestroyJavaVM();
        dlclose(library);
        return 73;
    }
    jmethodID mainMethod = env->GetStaticMethodID(entry, "main", "([Ljava/lang/String;)V");
    if (!mainMethod || env->ExceptionCheck()) {
        env->ExceptionDescribe();
        vm->DestroyJavaVM();
        dlclose(library);
        return 74;
    }
    jclass stringType = env->FindClass("java/lang/String");
    jobjectArray javaArgs = env->NewObjectArray(static_cast<jsize>(appArgs.size()),
                                               stringType, nullptr);
    for (size_t i = 0; i < appArgs.size(); ++i) {
        const auto utf16 = fromUtf8(appArgs[i]);
        jstring value = env->NewString(reinterpret_cast<const jchar*>(utf16.data()),
                                       static_cast<jsize>(utf16.size()));
        if (!value || env->ExceptionCheck()) {
            env->ExceptionDescribe();
            vm->DestroyJavaVM();
            dlclose(library);
            return 76;
        }
        env->SetObjectArrayElement(javaArgs, static_cast<jsize>(i), value);
        env->DeleteLocalRef(value);
    }
    env->CallStaticVoidMethod(entry, mainMethod, javaArgs);
    const bool failed = env->ExceptionCheck();
    if (failed)
        env->ExceptionDescribe();
    vm->DestroyJavaVM();
    dlclose(library);
    return failed ? 75 : 0;
}
