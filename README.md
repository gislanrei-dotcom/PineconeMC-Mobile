# PineconeMC Mobile — port nativo do PineconeMC (Android ARM64)

**Este projeto é o port nativo do PineconeMC original para Android; não utiliza nenhum launcher Android de terceiros como base.** Parte exclusivamente do [código-fonte oficial do PineconeMC](https://github.com/ElyPrismLauncher/Launcher), revisão fixada `9d6572797078947314b1f1737590bc157a259958`. O projeto oficial é escrito em C++20/Qt 6 e já contém o gerenciamento de instâncias, os downloads e a autenticação Ely.by.

## Por que ainda não há APK jogável?

O PineconeMC oficial é um aplicativo desktop. Os passos `JavaCheck` e `LaunchTask` executam Java como processo externo (`QProcess`). Android não fornece esse ambiente Java Edition nem as bibliotecas GLFW/LWJGL apropriadas. Portar o Qt para Android **não** faz o Minecraft rodar por si só.

Esta primeira etapa audita e tenta compilar o **código original** para a ABI `arm64-v8a`, com correções de CMake Android isoladas em `scripts/patch_native.py`. O workflow não publica um "APK" que só abre uma tela: falha explicitamente se o projeto nativo não puder ser compilado.

## Arquivos

- `.github/workflows/port-android-native.yml`: instalação Qt 6 para Android, NDK, dependências do PineconeMC e build CMake;
- `scripts/patch_native.py`: mudanças mínimas em CMake para tentar compilar o **próprio** PineconeMC;
- `PORT_STATUS.md`: progresso e o que falta validar.

## Política

Este port preserva os arquivos de licença do PineconeMC e sua árvore de código. PineconeMC em si é um fork GPL-3.0-only de Prism Launcher; usar o código oficial implica preservar esses avisos, e não exige motor de launcher Android externo. Java/OpenJDK, Android SDK/NDK e Qt são runtimes/ferramentas, não launchers substitutos.

O APK final só poderá ser chamado de funcional depois de rodar Minecraft Java no Android real e passar pelo login Ely.by.

**Branch principal:** a `main` contém apenas os arquivos ativos deste port nativo. O código do PineconeMC é obtido diretamente do repositório oficial durante a compilação.
