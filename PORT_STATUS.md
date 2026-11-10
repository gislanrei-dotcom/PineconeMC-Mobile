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
