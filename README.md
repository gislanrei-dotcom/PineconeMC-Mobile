# PineconeMC Mobile — Minecraft Java no Android (em desenvolvimento)

Projeto Android baseado no motor real do **FoldCraftLauncher**. O código modificado encontra-se em `PineconeMC-Mobile-fonte.zip` (camada `overlay/`) e é aplicado sobre a revisão fixa do FCL durante a compilação. Não é uma demonstração visual.

## Compilar no próprio GitHub (sem PC)

1. Acesse **Actions** no repositório.
2. Escolha **PineconeMC Mobile - Build APK**.
3. Toque em **Run workflow**.
4. Abra a execução concluída. Se o status for **Success**, baixe o artifact `PineconeMC-Mobile-ARM64`.
5. Extraia o arquivo ZIP baixado e instale `PineconeMC-Mobile.apk` no Android ARM64.

[Ver compilações](https://github.com/gislanrei-dotcom/PineconeMC-Mobile/actions/workflows/build-android.yml)

O workflow usa Android SDK 35, NDK 27, CMake, JDK 17 e Gradle Wrapper, testa integridade, arquitetura ARM64 e assinatura do APK. Quando ocorre falha, publica logs em `PineconeMC-Mobile-build-errors` sempre que disponíveis.

## Estado e limitações

- Execução Minecraft Java, controles e gerenciamento: dependem do motor FCL preservado.
- Ely.by: usa integração de autenticação Yggdrasil/Authlib Injector do launcher; exige teste de login real, skin e sessão no celular.
- Offline e Microsoft: previstos no código-base FCL; Microsoft pode exigir configuração OAuth.
- Fabric, Forge, Quilt, NeoForge, mods, shaders e modpacks: recursos herdados, sujeitos à compatibilidade de versão e ao hardware.
- Interface: continua baseada no FoldCraftLauncher e ainda não reproduz todas as telas do PineconeMC desktop.
- **Não considere este projeto concluído apenas porque o APK compilou.** Ainda são necessários testes funcionais no Redmi 13.

Consulte [BUILD.md](BUILD.md) para detalhes do overlay e das licenças. O projeto incorpora componentes GPL-3.0; preserve avisos e créditos de terceiros.
