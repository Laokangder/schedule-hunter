package com.example.schedulehunter;

import android.os.Bundle;
import android.content.Intent;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        registerPlugin(SystemNotificationPlugin.class);
        registerPlugin(DeviceCalendarPlugin.class);
        super.onCreate(savedInstanceState);
        SystemNotificationPlugin.handleShareIntent(this, getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        SystemNotificationPlugin.handleShareIntent(this, intent);
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
