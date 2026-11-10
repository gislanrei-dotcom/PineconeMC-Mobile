# PineconeMC Mobile — Minecraft Java no Android (em desenvolvimento)

Projeto Android baseado no motor real do **FoldCraftLauncher**. As alterações estão em `PineconeMC-Mobile-fonte.zip` (camada `overlay/`) e em `patches/`, aplicadas nessa ordem sobre a revisão fixa do FCL na compilação. O ZIP sozinho não representa as correções posteriores de Ely.by e da interface. Não é uma demonstração visual.

## Compilar no próprio GitHub (sem PC)

1. Acesse **Actions** no repositório.
2. Escolha **PineconeMC Mobile - Build APK**.
3. Toque em **Run workflow**.
4. Se o status for **Success**, abra a seção [Releases](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/releases).
5. Na versão de teste mais recente, baixe `PineconeMC-Mobile.apk` e instale no Android ARM64.

[Ver compilações](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/workflows/build-android.yml)

O workflow usa Android SDK 35, NDK 27, CMake, JDK 17 e Gradle Wrapper, testa integridade, arquitetura ARM64 e assinatura do APK. O APK é publicado como **pré-lançamento no GitHub Releases**, pois a conta atingiu o limite de armazenamento de artifacts do Actions. Quando ocorre falha, os logs permanecem disponíveis na própria execução do GitHub Actions.

## Estado e limitações

- Execução Minecraft Java, controles e gerenciamento: dependem do motor FCL preservado.
- Ely.by: a camada `patches/` encaminha autenticação de usuário aos endpoints oficiais `/auth/*`, preservando Authlib Injector para o jogo; exige teste de login real, skin e sessão no celular. Não aceita tokens nulos como sessões válidas.
- Offline e Microsoft: previstos no código-base FCL; Microsoft pode exigir configuração OAuth.
- Fabric, Forge, Quilt, NeoForge, mods, shaders e modpacks: recursos herdados, sujeitos à compatibilidade de versão e ao hardware.
- Interface: a tela inicial foi redesenhada como biblioteca de instâncias ao estilo PineconeMC, com versões reais e ações que abrem os gerenciadores FCL. As telas internas ainda não reproduzem integralmente a interface Qt de desktop.
- **Não considere este projeto concluído apenas porque o APK compilou.** Ainda são necessários testes funcionais no Redmi 13.

Consulte [BUILD.md](BUILD.md) para detalhes do overlay e das licenças. O projeto incorpora componentes GPL-3.0; preserve avisos e créditos de terceiros.

## APK de teste

[Baixar PineconeMC Mobile ARM64 – Build #3](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/releases/tag/pinecone-mobile-debug-3)

O GitHub Actions compilou, verificou a estrutura do APK, a arquitetura arm64-v8a e sua assinatura. Nenhuma autenticação Ely.by com credenciais reais nem inicialização do Minecraft foi testada em aparelho. Na atualização do aplicativo, não desinstale o anterior sem antes preservar as instâncias e configurações.
