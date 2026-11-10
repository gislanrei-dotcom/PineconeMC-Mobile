package com.tungsten.fcl.ui.main;

import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.GridLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import com.tungsten.fcl.setting.Accounts;
import com.tungsten.fcl.setting.ConfigHolder;
import com.tungsten.fcl.setting.Profile;
import com.tungsten.fcl.setting.Profiles;
import com.tungsten.fcl.ui.UIManager;
import com.tungsten.fcl.ui.account.CreateAccountDialog;
import com.tungsten.fcl.ui.download.DownloadUI;
import com.tungsten.fcl.ui.version.Versions;
import com.tungsten.fclcore.auth.Account;
import com.tungsten.fclcore.auth.authlibinjector.AuthlibInjectorServer;
import com.tungsten.fclcore.game.Version;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * Pinecone-style instance library for touchscreens. Every action is wired to
 * the existing FCL instance repository, installer, accounts or launch engine.
 * No fake data or placeholder buttons.
 */
public final class PineconeHomeView extends LinearLayout {
    private static final int BG = Color.rgb(22, 23, 25);
    private static final int PANEL = Color.rgb(32, 33, 36);
    private static final int CARD = Color.rgb(42, 43, 47);
    private static final int HIGHLIGHT = Color.rgb(65, 122, 88);
    private static final int TEXT = Color.rgb(235, 237, 239);
    private static final int MUTED = Color.rgb(165, 168, 170);
    private static final String ELY_URL = "https://authserver.ely.by/api/authlib-injector/";

    private final LinearLayout library;
    private final TextView accountLabel;
    private final TextView countLabel;
    private final TextView selectedLabel;
    private final TextView detailLabel;
    private final Button launchButton;
    private String selectedVersion;

    public PineconeHomeView(Context context) {
        super(context);
        setOrientation(VERTICAL);
        setBackgroundColor(BG);
        setPadding(dp(13), dp(10), dp(13), dp(10));
        setFocusable(true);

        LinearLayout header = new LinearLayout(context);
        header.setOrientation(HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        addView(header, new LayoutParams(LayoutParams.MATCH_PARENT, dp(44)));

        LinearLayout branding = new LinearLayout(context);
        branding.setOrientation(VERTICAL);
        TextView brand = text("PineconeMC", 22, TEXT, true);
        branding.addView(brand);
        TextView sub = text("MOBILE  •  MINECRAFT JAVA", 10, MUTED, false);
        branding.addView(sub);
        header.addView(branding, new LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f));

        accountLabel = text("", 12, MUTED, false);
        header.addView(accountLabel);
        header.addView(space(8));
        header.addView(button("Contas", false, () -> openAccounts()));
        header.addView(space(6));
        header.addView(button("Configurações", false, () -> openSettings()));

        LinearLayout topBar = new LinearLayout(context);
        topBar.setGravity(Gravity.CENTER_VERTICAL);
        topBar.setPadding(0, dp(12), 0, dp(9));
        addView(topBar, new LayoutParams(LayoutParams.MATCH_PARENT, dp(62)));

        HorizontalScrollView menuScroll = new HorizontalScrollView(context);
        menuScroll.setHorizontalScrollBarEnabled(false);
        topBar.addView(menuScroll);
        LinearLayout actions = new LinearLayout(context);
        actions.setGravity(Gravity.CENTER_VERTICAL);
        menuScroll.addView(actions);
        actions.addView(button("+ Adicionar instância", true, this::openInstaller));
        actions.addView(space(8));
        actions.addView(button("Instâncias", false, this::openVersions));
        actions.addView(space(8));
        actions.addView(button("Modpacks", false, () -> openDownload(DownloadUI.PAGE_ID_DOWNLOAD_MODPACK)));
        actions.addView(space(8));
        actions.addView(button("Mods", false, () -> openDownload(DownloadUI.PAGE_ID_DOWNLOAD_MOD)));
        actions.addView(space(8));
        actions.addView(button("Shaders", false, () -> openDownload(DownloadUI.PAGE_ID_DOWNLOAD_SHADER_PACK)));
        actions.addView(space(8));
        actions.addView(button("Atualizar", false, this::refresh));

        View line = new View(context);
        line.setBackgroundColor(Color.rgb(53, 54, 57));
        addView(line, new LayoutParams(LayoutParams.MATCH_PARENT, dp(1)));

        LinearLayout content = new LinearLayout(context);
        content.setOrientation(HORIZONTAL);
        addView(content, new LayoutParams(LayoutParams.MATCH_PARENT, 0, 1));

        LinearLayout mainPanel = new LinearLayout(context);
        mainPanel.setOrientation(VERTICAL);
        mainPanel.setPadding(dp(3), dp(14), dp(7), 0);
        content.addView(mainPanel, new LayoutParams(0, LayoutParams.MATCH_PARENT, 1f));

        LinearLayout rowTitle = new LinearLayout(context);
        rowTitle.setGravity(Gravity.CENTER_VERTICAL);
        mainPanel.addView(rowTitle);
        rowTitle.addView(text("Minhas instâncias", 18, TEXT, true), new LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f));
        countLabel = text("", 12, MUTED, false);
        rowTitle.addView(countLabel);
        TextView hint = text("Selecione uma instância para jogar ou gerenciar. As versões são lidas do armazenamento real.", 11, MUTED, false);
        hint.setPadding(0, dp(5), 0, dp(8));
        mainPanel.addView(hint);

        ScrollView listScroll = new ScrollView(context);
        listScroll.setFillViewport(true);
        mainPanel.addView(listScroll, new LayoutParams(LayoutParams.MATCH_PARENT, 0, 1));
        library = new LinearLayout(context);
        library.setOrientation(VERTICAL);
        listScroll.addView(library, new ScrollView.LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT));

        LinearLayout detail = new LinearLayout(context);
        detail.setOrientation(VERTICAL);
        detail.setPadding(dp(12), dp(13), dp(12), dp(10));
        detail.setBackground(round(PANEL, 12, Color.rgb(65, 66, 70), 1));
        int widthDp = getResources().getConfiguration().screenWidthDp;
        content.addView(detail, new LayoutParams(dp(widthDp < 670 ? 175 : 215), LayoutParams.MATCH_PARENT));
        detail.addView(text("INSTÂNCIA ATIVA", 11, MUTED, true));
        selectedLabel = text("Nenhuma versão", 17, TEXT, true);
        selectedLabel.setPadding(0, dp(10), 0, dp(4));
        detail.addView(selectedLabel);
        detailLabel = text("Instale uma versão para começar.", 12, MUTED, false);
        detail.addView(detailLabel);
        detail.addView(new View(context), new LayoutParams(1, 0, 1f));

        launchButton = button("▶  Jogar", true, this::launchSelected);
        detail.addView(launchButton, new LayoutParams(LayoutParams.MATCH_PARENT, dp(46)));
        detail.addView(verticalSpace(9));
        detail.addView(button("Gerenciar instâncias", false, this::openVersions), new LayoutParams(LayoutParams.MATCH_PARENT, dp(40)));
        detail.addView(verticalSpace(7));
        detail.addView(button("Adicionar Ely.by", false, this::openElyLogin), new LayoutParams(LayoutParams.MATCH_PARENT, dp(40)));
        detail.addView(verticalSpace(7));
        detail.addView(button("Nova versão", false, this::openInstaller), new LayoutParams(LayoutParams.MATCH_PARENT, dp(40)));

        refresh();
    }

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private TextView text(String label, int size, int color, boolean bold) {
        TextView view = new TextView(getContext());
        view.setText(label);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setGravity(Gravity.CENTER_VERTICAL);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    private GradientDrawable round(int fill, int corners, int stroke, int strokeWidth) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setCornerRadius(dp(corners));
        if (strokeWidth > 0) drawable.setStroke(dp(strokeWidth), stroke);
        return drawable;
    }

    private View space(int width) {
        View v = new View(getContext());
        v.setLayoutParams(new LayoutParams(dp(width), dp(1)));
        return v;
    }

    private View verticalSpace(int height) {
        View v = new View(getContext());
        v.setLayoutParams(new LayoutParams(1, dp(height)));
        return v;
    }

    private Button button(String label, boolean primary, Runnable callback) {
        Button button = new Button(getContext());
        button.setText(label);
        button.setTextSize(11);
        button.setAllCaps(false);
        button.setSingleLine(true);
        button.setTextColor(TEXT);
        button.setMinHeight(0);
        button.setMinimumHeight(0);
        button.setPadding(dp(10), 0, dp(10), 0);
        button.setBackground(round(primary ? HIGHLIGHT : CARD, 7, primary ? HIGHLIGHT : Color.rgb(63, 65, 68), 1));
        button.setOnClickListener(v -> callback.run());
        return button;
    }

    private void refreshDetails() {
        Profile profile = Profiles.getSelectedProfile();
        selectedVersion = profile.getSelectedVersion();
        selectedLabel.setText(selectedVersion == null ? "Nenhuma versão" : selectedVersion);
        detailLabel.setText(selectedVersion == null ? "Instale o Minecraft Java para começar." : "Pronta para iniciar com o motor FoldCraftLauncher");
        launchButton.setEnabled(selectedVersion != null && Accounts.getSelectedAccount() != null);
        launchButton.setAlpha(launchButton.isEnabled() ? 1f : .5f);
    }

    public void refresh() {
        if (!isAttachedToWindow()) {
            // This method is also called during construction; rendering is
            // allowed before attachment, but version loading may finish later.
        }
        Account account = Accounts.getSelectedAccount();
        accountLabel.setText(account == null ? "Sem conta" : account.getCharacter());
        Profile profile = Profiles.getSelectedProfile();
        library.removeAllViews();
        if (!profile.getRepository().isLoaded()) {
            countLabel.setText("Carregando...");
            library.addView(text("Carregando instâncias…", 14, MUTED, false));
            // Repositories are initialized by Profiles; never enumerate before isLoaded.
            refreshDetails();
            return;
        }
        List<Version> versions = new ArrayList<>(profile.getRepository().getVersions());
        versions.sort(Comparator.comparing(Version::getId, String.CASE_INSENSITIVE_ORDER));
        countLabel.setText(versions.size() + " versões");
        if (versions.isEmpty()) {
            TextView empty = text("Nenhuma instância instalada.\nUse '+ Adicionar instância' para instalar uma versão Vanilla, Fabric, Forge ou outra opção compatível.", 13, MUTED, false);
            empty.setPadding(dp(10), dp(20), dp(10), dp(20));
            library.addView(empty);
        } else {
            int width = getResources().getConfiguration().screenWidthDp;
            int columns = width < 730 ? 2 : 3;
            GridLayout grid = new GridLayout(getContext());
            grid.setColumnCount(columns);
            library.addView(grid);
            for (Version version : versions) {
                String versionId = version.getId();
                LinearLayout card = new LinearLayout(getContext());
                card.setOrientation(VERTICAL);
                card.setPadding(dp(12), dp(12), dp(12), dp(10));
                boolean chosen = versionId.equals(profile.getSelectedVersion());
                card.setBackground(round(chosen ? Color.rgb(34, 55, 43) : CARD, 9, chosen ? HIGHLIGHT : Color.rgb(58, 60, 64), chosen ? 2 : 1));
                GridLayout.LayoutParams cardParams = new GridLayout.LayoutParams();
                cardParams.width = dp(width < 670 ? 137 : (width < 890 ? 162 : 182));
                cardParams.height = dp(145);
                cardParams.setMargins(0, 0, dp(8), dp(8));
                grid.addView(card, cardParams);

                TextView icon = text("▦", 25, Color.rgb(124, 177, 129), true);
                card.addView(icon);
                TextView label = text(versionId, 12, TEXT, true);
                label.setSingleLine(true);
                label.setEllipsize(android.text.TextUtils.TruncateAt.END);
                card.addView(label);
                String lower = versionId.toLowerCase(Locale.ROOT);
                String type = lower.contains("neoforge") ? "NeoForge" : lower.contains("forge") ? "Forge"
                        : lower.contains("fabric") ? "Fabric" : lower.contains("quilt") ? "Quilt" : "Minecraft Java";
                card.addView(text(type, 10, MUTED, false));
                card.addView(new View(getContext()), new LayoutParams(1, 0, 1f));
                Button run = button("▶  Jogar", true, () -> {
                    profile.setSelectedVersion(versionId);
                    Versions.launch(getContext(), profile, versionId);
                });
                card.addView(run, new LayoutParams(LayoutParams.MATCH_PARENT, dp(36)));
                card.setOnClickListener(v -> {
                    profile.setSelectedVersion(versionId);
                    refresh();
                });
            }
        }
        refreshDetails();
    }

    private void openInstaller() {
        UIManager.getInstance().switchUI(UIManager.getInstance().getDownloadUI());
    }

    private void openDownload(int pageId) {
        UIManager ui = UIManager.getInstance();
        ui.switchUI(ui.getDownloadUI());
        ui.getDownloadUI().showDownloadPage(pageId);
    }

    private void openVersions() {
        UIManager.getInstance().switchUI(UIManager.getInstance().getVersionUI());
    }

    private void openAccounts() {
        UIManager.getInstance().switchUI(UIManager.getInstance().getAccountUI());
    }

    private void openSettings() {
        UIManager.getInstance().switchUI(UIManager.getInstance().getSettingUI());
    }

    private void launchSelected() {
        Profile profile = Profiles.getSelectedProfile();
        if (profile.getSelectedVersion() != null) {
            Versions.launch(getContext(), profile, profile.getSelectedVersion());
        }
    }

    private void openElyLogin() {
        AuthlibInjectorServer server = null;
        for (AuthlibInjectorServer current : ConfigHolder.config().getAuthlibInjectorServers()) {
            if (ELY_URL.equals(current.getUrl())) {
                server = current;
                break;
            }
        }
        if (server == null) {
            server = new AuthlibInjectorServer(ELY_URL);
            ConfigHolder.config().getAuthlibInjectorServers().add(server);
        }
        new CreateAccountDialog(getContext(), server).show();
    }
}
