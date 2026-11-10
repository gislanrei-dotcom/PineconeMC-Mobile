# Android package overlay (Qt 6.8)

`AndroidManifest.xml` is a small customization of the [Qt 6.8.3 Android template](https://github.com/qt/qtbase/blob/v6.8.3/src/android/templates/AndroidManifest.xml).

The app uses Qt's genuine `QtActivity`, **PineconeMC C++** as the entry point, and bundles the Qt 6.8 ARM64 libraries via `androiddeployqt`. We set:

- Package `ru.pineconemc.mobile` (separate from previous test APKs)
- Name `PineconeMC Mobile`
- Landscape orientation
- Network permission for authenticated downloads
- Android minimum API 28 (Android 9)

**This is not a complete game launcher yet.** Qt's Java Android Activity is not an OpenJDK Java Edition runtime. Minecraft and mod launch require an embedded compatible JVM, native LWJGL graphics, input and audio bridge, assets and account/session integration. They are not implemented simply by adding this manifest.

No alternative launcher is included or imported.
