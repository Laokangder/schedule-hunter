package com.example.schedulehunter;

import android.app.Notification;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.text.TextUtils;

import org.json.JSONObject;

import java.util.LinkedHashSet;
import java.util.Set;

public class ScheduleNotificationListenerService extends NotificationListenerService {
    @Override
    public void onNotificationPosted(StatusBarNotification statusBarNotification) {
        if (statusBarNotification == null || !NotificationCaptureStore.isEnabled(this)) return;
        if (getPackageName().equals(statusBarNotification.getPackageName())) return;

        Notification notification = statusBarNotification.getNotification();
        if (notification == null || shouldIgnore(notification)) return;

        Bundle extras = notification.extras;
        String title = readText(extras, Notification.EXTRA_TITLE);
        String text = readText(extras, Notification.EXTRA_TEXT);
        String bigText = readText(extras, Notification.EXTRA_BIG_TEXT);
        String subText = readText(extras, Notification.EXTRA_SUB_TEXT);
        String sourceText = joinUnique(title, text, bigText, subText);
        if (sourceText.isEmpty()
            || NotificationCaptureStore.containsSensitiveContent(sourceText)
            || !NotificationCaptureStore.containsScheduleHint(sourceText)) return;

        long capturedAt = System.currentTimeMillis();
        String signature = NotificationCaptureStore.sha256(
            statusBarNotification.getPackageName() + "|" + statusBarNotification.getKey() + "|" + sourceText
        );
        if (!NotificationCaptureStore.shouldCapture(this, signature, capturedAt)) return;

        JSONObject event = new JSONObject();
        try {
            event.put("event_id", NotificationCaptureStore.sha256(signature + "|" + capturedAt));
            event.put("notification_key", statusBarNotification.getKey());
            event.put("package_name", statusBarNotification.getPackageName());
            event.put("app_name", resolveAppName(statusBarNotification.getPackageName()));
            event.put("posted_at", statusBarNotification.getPostTime());
            event.put("captured_at", capturedAt);
            event.put("title", title);
            event.put("text", text);
            event.put("source_text", sourceText);
        } catch (Exception ignored) {
            return;
        }

        NotificationCaptureStore.enqueue(this, event);
        SystemNotificationPlugin.dispatchCaptured(event);
    }

    private boolean shouldIgnore(Notification notification) {
        if ((notification.flags & Notification.FLAG_GROUP_SUMMARY) != 0) return true;
        if ((notification.flags & Notification.FLAG_ONGOING_EVENT) != 0) return true;
        if (notification.category == null) return false;
        return Notification.CATEGORY_SERVICE.equals(notification.category)
            || Notification.CATEGORY_PROGRESS.equals(notification.category)
            || Notification.CATEGORY_SYSTEM.equals(notification.category);
    }

    private String resolveAppName(String packageName) {
        PackageManager manager = getPackageManager();
        try {
            ApplicationInfo info = manager.getApplicationInfo(packageName, 0);
            return manager.getApplicationLabel(info).toString();
        } catch (PackageManager.NameNotFoundException error) {
            return packageName;
        }
    }

    private String readText(Bundle extras, String key) {
        if (extras == null) return "";
        CharSequence value = extras.getCharSequence(key);
        return value == null ? "" : value.toString().trim();
    }

    private String joinUnique(String... values) {
        Set<String> unique = new LinkedHashSet<>();
        for (String value : values) {
            if (!TextUtils.isEmpty(value)) unique.add(value.trim());
        }
        return TextUtils.join("\n", unique);
    }
}
