package com.example.schedulehunter;

import android.content.Intent;
import android.provider.Settings;

import androidx.core.app.NotificationManagerCompat;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

@CapacitorPlugin(name = "SystemNotificationListener")
public class SystemNotificationPlugin extends Plugin {
    private static volatile SystemNotificationPlugin activeInstance;
    private static volatile boolean appForeground;

    @Override
    public void load() {
        activeInstance = this;
    }

    @Override
    protected void handleOnDestroy() {
        if (activeInstance == this) activeInstance = null;
    }

    @PluginMethod
    public void checkPermission(PluginCall call) {
        boolean granted = NotificationManagerCompat.getEnabledListenerPackages(getContext()).contains(getContext().getPackageName());
        JSObject result = new JSObject();
        result.put("supported", true);
        result.put("granted", granted);
        result.put("enabled", NotificationCaptureStore.isEnabled(getContext()));
        call.resolve(result);
    }

    @PluginMethod
    public void openPermissionSettings(PluginCall call) {
        try {
            Intent intent = new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
            getActivity().startActivity(intent);
            call.resolve();
        } catch (Exception error) {
            call.reject("无法打开系统通知使用权设置", error);
        }
    }

    @PluginMethod
    public void setEnabled(PluginCall call) {
        Boolean enabled = call.getBoolean("enabled", true);
        NotificationCaptureStore.setEnabled(getContext(), Boolean.TRUE.equals(enabled));
        JSObject result = new JSObject();
        result.put("enabled", Boolean.TRUE.equals(enabled));
        call.resolve(result);
    }

    @PluginMethod
    public void setBackendUrl(PluginCall call) {
        String backendUrl = call.getString("backendUrl", "");
        if (!backendUrl.isEmpty() && !backendUrl.startsWith("http://") && !backendUrl.startsWith("https://")) {
            call.reject("后端地址必须以 http:// 或 https:// 开头");
            return;
        }
        while (backendUrl.endsWith("/")) backendUrl = backendUrl.substring(0, backendUrl.length() - 1);
        NotificationCaptureStore.setBackendUrl(getContext(), backendUrl);
        JSObject result = new JSObject();
        result.put("configured", !backendUrl.isEmpty());
        call.resolve(result);
    }

    @PluginMethod
    public void getPending(PluginCall call) {
        JSONArray pending = NotificationCaptureStore.getPending(getContext());
        JSObject result = new JSObject();
        try {
            result.put("notifications", new JSArray(pending.toString()));
            call.resolve(result);
        } catch (JSONException error) {
            call.reject("读取待处理通知失败", error);
        }
    }

    @PluginMethod
    public void acknowledge(PluginCall call) {
        JSArray eventIds = call.getArray("eventIds", new JSArray());
        int removed = NotificationCaptureStore.acknowledge(getContext(), eventIds);
        JSObject result = new JSObject();
        result.put("removed", removed);
        call.resolve(result);
    }

    static void dispatchCaptured(JSONObject event) {
        SystemNotificationPlugin instance = activeInstance;
        if (instance == null || instance.getActivity() == null) return;
        instance.getActivity().runOnUiThread(() -> {
            try {
                instance.notifyListeners("notificationCaptured", JSObject.fromJSONObject(event), true);
            } catch (JSONException ignored) {}
        });
    }

    static boolean isAppForeground() {
        return appForeground;
    }

    static void setAppForeground(boolean foreground) {
        appForeground = foreground;
    }
}
