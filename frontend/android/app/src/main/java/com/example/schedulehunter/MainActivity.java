package com.example.schedulehunter;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        registerPlugin(SystemNotificationPlugin.class);
        super.onCreate(savedInstanceState);
    }

    @Override
    public void onStart() {
        super.onStart();
        SystemNotificationPlugin.setAppForeground(true);
    }

    @Override
    public void onStop() {
        SystemNotificationPlugin.setAppForeground(false);
        super.onStop();
    }
}
