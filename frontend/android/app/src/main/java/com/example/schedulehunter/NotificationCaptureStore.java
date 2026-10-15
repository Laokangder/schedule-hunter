package com.example.schedulehunter;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

final class NotificationCaptureStore {
    private static final String PREFS_NAME = "system_notification_capture";
    private static final String KEY_ENABLED = "enabled";
    private static final String KEY_QUEUE = "pending_notifications";
    private static final String KEY_DEDUPE = "notification_dedupe";
    private static final String KEY_BACKEND_URL = "backend_url";
    private static final int MAX_QUEUE_SIZE = 100;
    private static final long DEDUPE_WINDOW_MS = 2 * 60 * 1000L;
    private static final long DEDUPE_RETENTION_MS = 10 * 60 * 1000L;

    private static final Pattern SENSITIVE_PATTERN = Pattern.compile(
        "(验证码|校验码|动态码|一次性密码|otp|one[- ]?time password|password|passcode|支付密码|银行卡|银行余额|账户余额|付款码|收款码)",
        Pattern.CASE_INSENSITIVE
    );
    private static final Pattern SCHEDULE_HINT_PATTERN = Pattern.compile(
        "(今天|明天|后天|今晚|上午|下午|中午|晚上|凌晨|周[一二三四五六日天]|星期[一二三四五六日天]|礼拜[一二三四五六日天]|"
            + "\\d{1,2}\u6708\\d{1,2}\u65e5|\\d{1,2}[点时:：]\\d{0,2}|\\d+\\s*(分钟|小时|天)后|"
            + "today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\\d{1,2}:\\d{2})",
        Pattern.CASE_INSENSITIVE
    );

    private NotificationCaptureStore() {}

    static synchronized boolean isEnabled(Context context) {
        return preferences(context).getBoolean(KEY_ENABLED, true);
    }

    static synchronized void setEnabled(Context context, boolean enabled) {
        preferences(context).edit().putBoolean(KEY_ENABLED, enabled).apply();
    }

    static synchronized void setBackendUrl(Context context, String backendUrl) {
        preferences(context).edit().putString(KEY_BACKEND_URL, backendUrl == null ? "" : backendUrl.trim()).apply();
    }

    static synchronized String getBackendUrl(Context context) {
        return preferences(context).getString(KEY_BACKEND_URL, "");
    }

    static boolean containsSensitiveContent(String text) {
        return text != null && SENSITIVE_PATTERN.matcher(text).find();
    }

    static boolean containsScheduleHint(String text) {
        return text != null && SCHEDULE_HINT_PATTERN.matcher(text).find();
    }

    static synchronized boolean shouldCapture(Context context, String signature, long now) {
        SharedPreferences prefs = preferences(context);
        Map<String, Long> entries = readDedupeEntries(prefs.getString(KEY_DEDUPE, "{}"));
        entries.entrySet().removeIf(entry -> now - entry.getValue() > DEDUPE_RETENTION_MS);

        Long previous = entries.get(signature);
        if (previous != null && now - previous < DEDUPE_WINDOW_MS) {
            writeDedupeEntries(prefs, entries);
            return false;
        }

        entries.put(signature, now);
        writeDedupeEntries(prefs, entries);
        return true;
    }

    static synchronized void enqueue(Context context, JSONObject event) {
        SharedPreferences prefs = preferences(context);
        JSONArray current = readArray(prefs.getString(KEY_QUEUE, "[]"));
        JSONArray next = new JSONArray();
        int start = Math.max(0, current.length() - (MAX_QUEUE_SIZE - 1));
        for (int index = start; index < current.length(); index++) {
            JSONObject item = current.optJSONObject(index);
            if (item != null) next.put(item);
        }
        next.put(event);
        prefs.edit().putString(KEY_QUEUE, next.toString()).apply();
    }

    static synchronized JSONArray getPending(Context context) {
        return readArray(preferences(context).getString(KEY_QUEUE, "[]"));
    }

    static synchronized JSONObject attachParsedResponse(Context context, String eventId, JSONObject response) {
        SharedPreferences prefs = preferences(context);
        JSONArray current = readArray(prefs.getString(KEY_QUEUE, "[]"));
        JSONArray next = new JSONArray();
        JSONObject updated = null;
        for (int index = 0; index < current.length(); index++) {
            JSONObject item = current.optJSONObject(index);
            if (item == null) continue;
            if (eventId.equals(item.optString("event_id"))) {
                try {
                    item.put("parsed_response", response);
                    item.put("parsed_at", System.currentTimeMillis());
                    updated = item;
                } catch (JSONException ignored) {}
            }
            next.put(item);
        }
        prefs.edit().putString(KEY_QUEUE, next.toString()).commit();
        return updated;
    }

    static synchronized int acknowledge(Context context, JSONArray eventIds) {
        Set<String> ids = new HashSet<>();
        if (eventIds != null) {
            for (int index = 0; index < eventIds.length(); index++) {
                String id = eventIds.optString(index, "");
                if (!id.isEmpty()) ids.add(id);
            }
        }

        SharedPreferences prefs = preferences(context);
        JSONArray current = readArray(prefs.getString(KEY_QUEUE, "[]"));
        JSONArray next = new JSONArray();
        int removed = 0;
        for (int index = 0; index < current.length(); index++) {
            JSONObject item = current.optJSONObject(index);
            if (item == null) continue;
            if (ids.contains(item.optString("event_id"))) {
                removed++;
            } else {
                next.put(item);
            }
        }
        prefs.edit().putString(KEY_QUEUE, next.toString()).apply();
        return removed;
    }

    static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder();
            for (byte item : bytes) result.append(String.format(Locale.US, "%02x", item));
            return result.toString();
        } catch (NoSuchAlgorithmException error) {
            return Integer.toHexString(value.hashCode());
        }
    }

    private static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    private static JSONArray readArray(String raw) {
        try {
            return new JSONArray(raw == null ? "[]" : raw);
        } catch (JSONException error) {
            return new JSONArray();
        }
    }

    private static Map<String, Long> readDedupeEntries(String raw) {
        Map<String, Long> result = new HashMap<>();
        try {
            JSONObject object = new JSONObject(raw == null ? "{}" : raw);
            Iterator<String> keys = object.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                result.put(key, object.optLong(key, 0L));
            }
        } catch (JSONException ignored) {}
        return result;
    }

    private static void writeDedupeEntries(SharedPreferences prefs, Map<String, Long> entries) {
        JSONObject object = new JSONObject();
        for (Map.Entry<String, Long> entry : entries.entrySet()) {
            try {
                object.put(entry.getKey(), entry.getValue());
            } catch (JSONException ignored) {}
        }
        prefs.edit().putString(KEY_DEDUPE, object.toString()).apply();
    }
}
