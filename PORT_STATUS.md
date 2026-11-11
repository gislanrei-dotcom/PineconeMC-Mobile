# Estado técnico do port original

Fonte: ElyPrismLauncher/Launcher, revisão `9d6572797078947314b1f1737590bc157a259958`, branch `develop`.

## Código original identificado

- **C++20 + Qt 6.8+ (Widgets, Network, NetworkAuth, Concurrent, OpenGL, XML)** e CMake.
- Mecanismo PineconeMC de instâncias, versões, modloaders, recursos e downloads mantido em `launcher/`.
- Autenticação OAuth2 Ely.by original em `launcher/minecraft/auth/` e APIs de Pinecone.
- Dependências nativas: libarchive, zlib, libqrencode, cmark, tomlplusplus, libnbt++ e bibliotecas internas.
- Licença principal GPL-3.0-only, mais avisos de terceiros.

## Trabalho em curso

1. Configuração de Qt/CMake para Android arm64-v8a, sem importar código de outro launcher.
2. Identificação de erros de compilação e dos trechos desktop que precisam ser adaptados.
3. Novo backend nativo Android para Java Edition (OpenJDK arm64 + JNI + EGL/OpenGL ES + entrada touchscreen): **não implementado**.
4. Teste com conta Ely.by, instâncias, mods e lançamento Minecraft real: **não realizado**.

### Regra de entrega

Um APK produzido apenas por Qt não representa um launcher jogável. Não publicar APK como pronto sem verificar carregamento do runtime Java, lançamento de jogo e autenticação em dispositivo.

## Relevância do AppImage

`PineconeMC-Linux-x86_64.AppImage` é um artefato compilado de Linux x64, inadequado ao Android ARM64; serve como referência visual e de versão, não como executável ou biblioteca Android.

PineconeMC oficialmente deriva de Prism Launcher; o port Android desta branch, porém, não usa o motor de um **outro launcher Android**.

## Compilações verificadas em 10/11/2026

- A primeira compilação nativa, execução `42803667404`, chegou ao CMake e revelou um erro de localização do pacote host ECM. Corrigido com `ECM_DIR`.
- A segunda, execução `42807464302`, passou pelo ECM e encontrou `Qt6NetworkAuth` ausente no pacote Android. O workflow agora instala o addon oficial `qtnetworkauth` via aqtinstall. Verificação de compilação subsequente pendente.
- Os pré-lançamentos antigos `pinecone-mobile-debug-2` e `pinecone-mobile-debug-3` foram excluídos em `42807417913`; a `main` atual não contém o código-fonte do antigo launcher Android.

Esta etapa verifica apenas a compilação do próprio PineconeMC em Android. A ponte nativa para JVM, gráficos e touchscreen ainda precisa ser implementada e validada. Não divulgar um APK apenas de interface como se estivesse jogável.

- A compilação nativa #4, execução `42810691586`, passou por CMake e iniciou a compilação C++ (150 de 456 objetos alcançados), mas falhou por `gamemode_client.h` (Feral GameMode exclusivo de Linux desktop). O script agora exclui esses blocos Linux do build Android sem alterar o motor PineconeMC. Nova execução: `42813154215`.

## Empacotamento Android (após a compilação C++ ARM64)

A compilação #8 `42820792083` passou integralmente pelo compilador e linker Qt Android, gerando o módulo nativo `libelyprismlauncher_arm64-v8a.so`. Foi acrescentado um pacote Android nativo com `androiddeployqt` (`cmake --build build-android --target apk`), manifesto Android próprio e validação automática por `aapt`, ZIP e ABI. O arquivo, **se a etapa de empacotamento passar**, será enviado somente como artefato `PineconeMC-Native-ARM64-UI-SMOKE-ONLY` do GitHub Actions. Não é lançado como versão jogável.

**Ainda faltam** execução de OpenJDK Java Edition (JVM ARM64 Android), LWJGL/OpenGL bridge, audio/touchscreen e ensaio real de inicialização e login no aparelho. O workflow não afirma que um APK com Qt implica que Minecraft está jogável.

## Mudanças após a Build #8

- Novo manifesto Qt Android com pacote `ru.pineconemc.mobile`, orientação horizontal e permissão INTERNET.
- Pipeline de `androiddeployqt` para APK ARM64 de diagnóstico; validação com `aapt` e integridade ZIP.
- Empacotamento dos **JARs originais PineconeMC** (`NewLaunch.jar`, `NewLaunchLegacy.jar`, `JavaCheck.jar`) como assets Android, com extração atômica para a pasta privada de dados do aplicativo.
- Caminhos de instâncias, arquivos e logs alterados no port para `QStandardPaths::AppDataLocation` no Android.
- Limitação em GitHub Actions: desde a execução `42826699679`, novos jobs falham antes de receber um runner, inclusive um simples `echo`, usando tanto `ubuntu-24.04` quanto `ubuntu-latest`. Sem runner, o APK **não foi gerado e não foi testado**. A causa específica não está acessível; pode exigir verificar Billing & Licensing/Usage ou a mensagem na página Actions da conta.
- Issue de acompanhamento: `https://github.com/gislanrei-dotcom/PineconeMC-Mobile/issues/1`.

O runtime OpenJDK/LWJGL e o controle touchscreen ainda não foram implementados; o trabalho de pacotes e JARs é infraestrutura, não o motor de execução de Minecraft.

## Detector de runtime Java 17 no Android

O arquivo `android/native/AndroidRuntime.cpp` consulta `nativeLibraryDir` via JNI e verifica a presença do futuro executável Java, `libjvm.so` e módulos Java 17. `CheckJava.cpp` passa a exibir erro explícito em português se o runtime ainda não estiver disponível, em vez de tentar usar o Java desktop. **O runtime e a ponte LWJGL ainda não estão implementados.** O Android impede executar binários de diretórios graváveis do app com target SDK moderno; o Java executável terá de ser incluído no APK.


## Atualização comprovada — 11/11/2026

**As notas mais antigas acima são histórico e descrevem condições que já mudaram.**

- A restrição do Actions foi resolvida ao tornar o projeto público: runner Ubuntu e Windows iniciaram; o bloqueio de faturamento anterior não está mais ativo.
- A [Build #33](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/runs/43083877125) **terminou com sucesso**, entregando um APK assinado **apenas para teste da interface Qt**. Nem inicialização em aparelho nem Minecraft jogável foram verificados.
- O processo Java JNI separado `libpinecone_java.so` teve cross-compilation AArch64 validada no [teste independente](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/runs/43093150921). A Build #35 testa a inclusão no pacote Qt Android, mas estava em execução na última verificação.
- Uma [auditoria específica de OpenJDK 17 ARM64 Android](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/runs/43093916689) identificou o pacote oficial Termux `17.0.21-2`: o `libjvm.so` é AArch64/Bionic, mas seu RUNPATH aponta para `/data/data/com.termux/files/usr`, há dependência direta `libandroid-shmem.so`, e a instalação JDK ocupa 213 MB. Não foi incluída no APK: exige adaptação e provas de execução/redistribuição.
- A lógica original de instâncias e autenticação permanece na árvore C++; **execução Java SE real, GLFW/LWJGL/EGL, áudio e toque para o jogo seguem pendentes**.
