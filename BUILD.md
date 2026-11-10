# PineconeMC Mobile — port em desenvolvimento

Esta árvore contém as alterações sobre Fold Craft Launcher f5bb1526eb371d81cb086d74cdb8535043b51ee4. O ícone vem de PineconeMC 9d6572797078947314b1f1737590bc157a259958. As licenças do projeto base permanecem no fonte materializado. Consulte também overlay/PINECONE-COPYING.md.

O pacote de desenvolvimento br.pinecone.mobile.debug tem identidade Android própria. Usa o runtime, os controles e a interface mobile da base FCL, inclui Ely.by entre os servidores de autenticação na primeira inicialização e ajusta a leitura de ZIPs de instâncias MultiMC/Pinecone que tenham nome de pasta diferente do nome exibido. Microsoft e importadores de mods seguem o código do FCL. O fluxo OAuth de navegador específico do Pinecone desktop e as substituições de Authlib dele não foram portados. A opção Ely.by usa o mecanismo de autenticação de terceiros do FCL.

## Compilar

Para compilar com GitHub Actions, coloque o conteúdo deste ZIP na raiz de um repositório, incluindo .github e overlay. Execute o workflow PineconeMC Mobile ARM64. O workflow tenta gerar e anexar o APK. Configure OAUTH_API_KEY para a integração Microsoft da base e CURSE_API_KEY para CurseForge quando necessário. A chave de debug do runner pode mudar entre execuções.

Para um build local com Android SDK, JDK 17 e acesso aos repositórios de dependências:

    python preparar.py FoldCraftLauncher-main.zip projeto-android
    cd projeto-android
    ./gradlew :FCL:assembleFordebug -Darch=arm64

No Windows use gradlew.bat. Saída esperada em FCL/build/outputs/apk/fordebug/.

## Verificação

O projeto foi materializado a partir do ZIP e foram conferidos recursos ARM64, ícones e alterações na árvore. A compilação local não passou do bootstrap do Gradle por falta de acesso à distribuição. A abertura do Minecraft, o login, a importação real de instâncias e os mods ainda aguardam teste. Nenhum APK vem neste ZIP.
