# PineconeMC Mobile — port nativo Android ARM64

Este projeto porta **o PineconeMC original** (código C++20/Qt 6), sem usar FoldCraftLauncher, Pojav ou outro launcher Android como base. A fonte original é [ElyPrismLauncher/Launcher](https://github.com/ElyPrismLauncher/Launcher) no commit fixado `9d6572797078947314b1f1737590bc157a259958`.

## Estado comprovado em 11/11/2026

- **[Build #33 — concluída com sucesso](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/runs/43083877125):** compilou o código C++ original para ARM64, criou e assinou um **APK de diagnóstico da interface Qt**, verificou bibliotecas ARM64, o pacote `ru.pineconemc.mobile` e os três JARs Java do projeto. O artefato `PineconeMC-Native-ARM64-UI-SMOKE-ONLY` contém o APK e está disponível no GitHub Actions por tempo limitado. **Não foi testado instalado em um celular.**
- **[Teste JNI nativo — concluído com sucesso](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/runs/43093150921):** compilou o novo processo `libpinecone_java.so` com NDK para AArch64 e verificou o formato ELF. O protótipo também passou em testes de execução com Java 21 no Linux; isso **não valida uma JVM Java SE no Android**.
- **[Build de integração JNI + Qt](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/runs/43093151155):** iniciada para incluir esse processo no APK (commit `1626f60d`). A aprovação do teste JNI isolado não implica que o APK integrado já tenha terminado.
- **[Auditoria OpenJDK 17 Android](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/runs/43093916689):** o pacote Bionic do Termux foi inspecionado, **sem distribuí-lo**. Ocupa cerca de 213 MB instalado, tem dependências nativas e caminhos absolutos `/data/data/com.termux/`, que impedem supor que funcionará diretamente em outro aplicativo.

### Ainda não é um launcher jogável

**Faltam:** runtime OpenJDK 17 realmente adaptado ao espaço privado deste aplicativo e suas bibliotecas nativas; carregamento do jogo; ponte LWJGL/GLFW para EGL/OpenGL ES ou Vulkan; áudio; controles touchscreen; testes no aparelho e login Ely.by. O APK da Build #33 é exclusivamente um **teste da interface**, não executa Minecraft Java.

## Estrutura do repositório

- `scripts/patch_native.py`: adapta a fonte do PineconeMC original ao Android/Qt sem substituí-la.
- `android/AndroidManifest.xml` e `android/native/AndroidRuntime.cpp`: aplicação Android e pré-requisitos de runtime.
- `android/runtime/JavaRunner.cpp`: processo JNI independente para uma futura JVM Java SE; não é Android ART nem contém OpenJDK.
- `scripts/test_java_runner.sh`: testes do adaptador Java com uma JVM Linux host.
- `scripts/validate_apk.py`: validação estrutural e de ABI do APK de teste.
- `.github/workflows/port-android-native.yml`: compilação e empacotamento ARM64.
- `.github/workflows/runner-android-native.yml`: compilação isolada do executável JNI ARM64.
- `.github/workflows/openjdk-android-audit.yml`: auditoria de dependências do runtime, sem importar binários de terceiros.

Este port preserva a árvore e os avisos de licença do projeto original. Código principal GPL-3.0-only. Toda eventual distribuição de um runtime OpenJDK deverá respeitar as licenças e notificações correspondentes.

**Acompanhamento:** [issue #1](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/issues/1).
