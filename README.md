# PineconeMC Mobile — port nativo do PineconeMC (Android ARM64)

**Este projeto é o port nativo do PineconeMC original para Android; não utiliza nenhum launcher Android de terceiros como base.** Parte exclusivamente do [código-fonte oficial do PineconeMC](https://github.com/ElyPrismLauncher/Launcher), revisão fixada `9d6572797078947314b1f1737590bc157a259958`. O projeto oficial é escrito em C++20/Qt 6 e já contém o gerenciamento de instâncias, os downloads e a autenticação Ely.by.

## Estado atualizado em 10/11/2026

**Concluído no código:** C++/Qt oficial compilado para Android ARM64 na Build #8; empacotamento Qt APK de diagnóstico preparado; manifesto, armazenamento interno Android, JARs de inicialização PineconeMC, ícone oficial, verificação de ELF ARM64 e assinatura. O detector do OpenJDK está ligado ao `CheckJava`, e existe um protótipo nativo independente de inicializador Java baseado em `JNI_CreateJavaVM`, disponível em `android/runtime/JavaRunner.cpp` (desativado na compilação padrão).

**Pendente:** produzir OpenJDK para Android/Bionic, incluir `libjvm.so` e módulos da JVM, compilar/testar o processo Java, integrar LWJGL, renderização, áudio e controles touchscreen, e validar o launcher no celular. **Nenhum APK foi gerado ou publicado a partir das alterações recentes** e não foi verificado gameplay nem login Ely.by.

**Bloqueio atual do CI:** GitHub Actions não está atribuindo runners para novos jobs (`runner_id=0`, `steps=[]`), inclusive num teste mínimo de shell sem dependências. A configuração de cobrança/limites do GitHub pode explicar isso, mas não foi possível confirmar pelo conector. Consultar [Actions](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions) e a [issue de acompanhamento](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/issues/1).

## Por que ainda não há APK jogável?

O PineconeMC oficial é um aplicativo desktop. Os passos `JavaCheck` e `LaunchTask` executam Java como processo externo (`QProcess`). Android não fornece esse ambiente Java Edition nem as bibliotecas GLFW/LWJGL apropriadas. Portar o Qt para Android **não** faz o Minecraft rodar por si só.

A compilação nativa **C++20/Qt 6.8 para Android ARM64 foi concluída** em [Build #8](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/runs/42820792083). O workflow seguinte prepara um APK Android com o mesmo código C++, os JARs de inicialização oficiais do PineconeMC, armazenamento privado e verificações do pacote. O resultado é apenas um **teste de integração da interface**, não um launcher jogável; por isso não é publicado em Releases.

## Arquivos

- `.github/workflows/port-android-native.yml`: instalação Qt 6 para Android, NDK, dependências do PineconeMC e build CMake;
- `scripts/patch_native.py`: correções de Qt/CMake e diretórios/arquivos Java do **próprio** PineconeMC para Android;
- `android/AndroidManifest.xml`: pacote Android horizontal, permissões e QtActivity;
- `scripts/validate_apk.py`: valida o APK e os JARs originais (sem certificar execução de Minecraft);
- `PORT_STATUS.md`: progresso e o que falta validar.

## Política

Este port preserva os arquivos de licença do PineconeMC e sua árvore de código. PineconeMC em si é um fork GPL-3.0-only de Prism Launcher; usar o código oficial implica preservar esses avisos, e não exige motor de launcher Android externo. Java/OpenJDK, Android SDK/NDK e Qt são runtimes/ferramentas, não launchers substitutos.

O APK final só poderá ser chamado de funcional depois de rodar Minecraft Java no Android real e passar pelo login Ely.by.

**Branch principal:** a `main` contém apenas os arquivos ativos deste port nativo. O código do PineconeMC é obtido diretamente do repositório oficial durante a compilação.

## Bloqueio atual de compilação

GitHub Actions não está conseguindo atribuir runner a nenhum workflow novo: inclusive o teste mínimo em `ubuntu-latest` falhou com `runner_id=0` e nenhuma etapa iniciada. O bloqueio começou depois da Build #8. A causa não foi identificada pelo conector; verificar a mensagem no [Actions](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions) e, se necessário, em **Settings → Billing & Licensing → Usage**. Limites/cobrança de Actions são uma possibilidade, não uma confirmação.

O acompanhamento das etapas restantes está na [issue #1](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/issues/1). O projeto não utiliza FoldCraftLauncher nem outro launcher Android como base.
