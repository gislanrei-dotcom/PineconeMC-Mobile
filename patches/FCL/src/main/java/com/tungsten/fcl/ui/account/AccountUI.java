package com.tungsten.fcl.ui.account;

import android.content.Context;
import android.view.View;
import android.widget.ListView;

import androidx.appcompat.widget.LinearLayoutCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.tungsten.fcl.R;
import com.tungsten.fcl.setting.Accounts;
import com.tungsten.fcl.setting.ConfigHolder;
import com.tungsten.fclcore.auth.authlibinjector.AuthlibInjectorServer;
import com.tungsten.fclcore.task.Task;
import com.tungsten.fcllibrary.component.ui.FCLCommonUI;

import java.util.ArrayList;
import java.util.stream.Collectors;

public class AccountUI extends FCLCommonUI implements View.OnClickListener {

    private LinearLayoutCompat addOfflineAccount;
    private LinearLayoutCompat addElyAccount;
    private LinearLayoutCompat addMicrosoftAccount;
    private LinearLayoutCompat addLoginServer;

    private RecyclerView recyclerView;
    private AccountListAdapter accountListAdapter;

    public AccountUI(Context context, int id) {
        super(context, id);
    }

    @Override
    public void onCreate() {
        super.onCreate();

        addOfflineAccount = findViewById(R.id.offline);
        addElyAccount = findViewById(R.id.pinecone_ely_account);
        addMicrosoftAccount = findViewById(R.id.microsoft);
        addLoginServer = findViewById(R.id.add_login_server);
        addOfflineAccount.setOnClickListener(this);
        addElyAccount.setOnClickListener(this);
        addMicrosoftAccount.setOnClickListener(this);
        addLoginServer.setOnClickListener(this);

        recyclerView = findViewById(R.id.recycler_view);
        recyclerView.setLayoutManager(new LinearLayoutManager(getContext()));

        ListView serverListView = findViewById(R.id.server_list);
        serverListView.setAdapter(new ServerListAdapter(getContext()));

        // 首次创建即刷新账户列表（原 onStart 生命周期，页面随重建重新初始化）
        loadAccounts();
    }

    public void loadAccounts() {
        ArrayList<AccountListItem> accountList = Accounts.getAccounts().stream()
                .map(account -> new AccountListItem(getContext(), account))
                .collect(Collectors.toCollection(ArrayList::new));
        if (accountListAdapter == null) {
            accountListAdapter = new AccountListAdapter(getContext(), accountList);
            recyclerView.setAdapter(accountListAdapter);
        } else {
            accountListAdapter.refresh(accountList);
        }
    }

    @Override
    public void onClick(View view) {
        if (view == addOfflineAccount) {
            CreateAccountDialog dialog = new CreateAccountDialog(getContext(), Accounts.FACTORY_OFFLINE);
            dialog.show();
        }
        if (view == addElyAccount) {
            final String url = "https://authserver.ely.by/api/authlib-injector/";
            AuthlibInjectorServer ely = null;
            for (AuthlibInjectorServer candidate : ConfigHolder.config().getAuthlibInjectorServers()) {
                if (url.equals(candidate.getUrl())) {
                    ely = candidate;
                    break;
                }
            }
            if (ely == null) {
                ely = new AuthlibInjectorServer(url);
                ConfigHolder.config().getAuthlibInjectorServers().add(ely);
            }
            new CreateAccountDialog(getContext(), ely).show();
        }
        if (view == addMicrosoftAccount) {
            CreateAccountDialog dialog = new CreateAccountDialog(getContext(), Accounts.FACTORY_MICROSOFT);
            dialog.show();
        }
        if (view == addLoginServer) {
            AddAuthlibInjectorServerDialog dialog = new AddAuthlibInjectorServerDialog(getContext());
            dialog.show();
        }
    }

}
