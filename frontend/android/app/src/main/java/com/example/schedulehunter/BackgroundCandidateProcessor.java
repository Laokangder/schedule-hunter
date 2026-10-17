package com.example.schedulehunter;

import android.Manifest;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.util.Log;

import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

final class BackgroundCandidateProcessor {
    private static final String TAG = "ScheduleCandidate";
    private static final String CHANNEL_ID = "schedule_candidates";
    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();

    private BackgroundCandidateProcessor() {}

    static void process(Context context, JSONObject event) {
        Context appContext = context.getApplicationContext();
        EXECUTOR.execute(() -> parseAndNotify(appContext, event));
    }

    private static void parseAndNotify(Context context, JSONObject event) {
        String backendUrl = NotificationCaptureStore.getBackendUrl(context);
        String sourceText = event.optString("source_text", "").trim();
        String eventId = event.optString("event_id", "");
        if (backendUrl.isEmpty() || sourceText.isEmpty() || eventId.isEmpty()) return;

        HttpURLConnection connection = null;
        try {
            URL url = new URL(backendUrl + "/api/v1/task/parse");
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(10_000);
            connection.setReadTimeout(20_000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");

            JSONObject body = buildRequest(eventId, sourceText);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body.toString().getBytes(StandardCharsets.UTF_8));
            }

            int status = connection.getResponseCode();
            InputStream stream = status >= 200 && status < 300 ? connection.getInputStream() : connection.getErrorStream();
            String rawResponse = readStream(stream);
            if (status < 200 || status >= 300 || rawResponse.isEmpty()) {
                Log.w(TAG, "Background parse failed with HTTP " + status);
                return;
            }

            JSONObject response = new JSONObject(rawResponse);
            if (response.optInt("code", -1) != 0) {
                Log.i(TAG, "Captured notification was not accepted as a schedule candidate");
                return;
            }

            JSONObject updatedEvent = NotificationCaptureStore.attachParsedResponse(context, eventId, response);
            if (updatedEvent == null) return;

            if (SystemNotificationPlugin.isAppForeground()) {
                SystemNotificationPlugin.dispatchCaptured(updatedEvent);
            } else {
                showCandidateNotification(context, updatedEvent, response);
            }
        } catch (Exception error) {
            Log.w(TAG, "Background candidate parsing failed: " + error.getClass().getSimpleName());
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static JSONObject buildRequest(String eventId, String sourceText) throws Exception {
        JSONObject preferences = new JSONObject();
        preferences.put("default_duration_minutes", 60);
        preferences.put("timezone", "Asia/Shanghai");

        JSONObject context = new JSONObject();
        context.put("recent_tasks", new org.json.JSONArray());
        context.put("user_preferences", preferences);

        JSONObject meta = new JSONObject();
        meta.put("input_type", "notification");
        meta.put("client_timestamp", isoTimestamp());
        meta.put("app_version", "1.0.0");

        JSONObject body = new JSONObject();
        body.put("request_id", "notification_" + eventId.substring(0, Math.min(16, eventId.length())));
        body.put("source_text", sourceText);
        body.put("context", context);
        body.put("meta", meta);
        return body;
    }

    private static String isoTimestamp() {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("Asia/Shanghai"));
        return format.format(new Date());
    }

    private static String readStream(InputStream stream) throws Exception {
        if (stream == null) return "";
        StringBuilder result = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) result.append(line);
        }
        return result.toString();
    }

    static void showCandidateNotification(Context context, JSONObject event, JSONObject response) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
            && ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;

        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(CHANNEL_ID, "候选日程", NotificationManager.IMPORTANCE_HIGH);
            channel.setDescription("从其他应用通知中识别出的待确认日程");
            manager.createNotificationChannel(channel);
        }

        JSONObject data = response.optJSONObject("data");
        JSONObject parsed = data == null ? null : data.optJSONObject("parsed");
        if (parsed == null) return;

        String taskTitle = parsed.optString("title", "待确认日程");
        String startTime = compactTime(parsed.optString("start_time", ""));
        String location = parsed.optString("location", "");
        boolean conflict = data.optBoolean("is_conflict", false);
        StringBuilder summary = new StringBuilder(taskTitle);
        if (!startTime.isEmpty()) summary.append(" · ").append(startTime);
        if (!location.isEmpty()) summary.append(" · ").append(location);

        Intent intent = new Intent(context, MainActivity.class);
        intent.putExtra("captured_event_id", event.optString("event_id", ""));
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        int requestCode = stableNotificationId(event.optString("event_id", "candidate"));
        PendingIntent pendingIntent = PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Intent openAction = new Intent(context, CandidateActionReceiver.class)
            .setAction(CandidateActionReceiver.ACTION_OPEN)
            .putExtra(CandidateActionReceiver.EXTRA_EVENT_ID, event.optString("event_id", ""));
        PendingIntent confirmIntent = PendingIntent.getBroadcast(
            context,
            requestCode ^ 0x101,
            openAction,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        PendingIntent snooze10Intent = candidateActionIntent(context, event.optString("event_id", ""), 10, requestCode ^ 0x102);
        PendingIntent snooze60Intent = candidateActionIntent(context, event.optString("event_id", ""), 60, requestCode ^ 0x103);
        Intent ignoreAction = new Intent(context, CandidateActionReceiver.class)
            .setAction(CandidateActionReceiver.ACTION_IGNORE)
            .putExtra(CandidateActionReceiver.EXTRA_EVENT_ID, event.optString("event_id", ""));
        PendingIntent ignoreIntent = PendingIntent.getBroadcast(
            context,
            requestCode ^ 0x104,
            ignoreAction,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(conflict ? "发现冲突日程，等待确认" : "发现候选日程")
            .setContentText(summary.toString())
            .setStyle(new NotificationCompat.BigTextStyle().bigText(summary.toString()))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .addAction(0, "查看确认", confirmIntent)
            .addAction(0, "10分钟后", snooze10Intent)
            .addAction(0, "1小时后", snooze60Intent)
            .addAction(0, "忽略", ignoreIntent);
        manager.notify(requestCode, builder.build());
    }

    private static PendingIntent candidateActionIntent(Context context, String eventId, int delayMinutes, int requestCode) {
        Intent action = new Intent(context, CandidateActionReceiver.class)
            .setAction(CandidateActionReceiver.ACTION_SNOOZE)
            .putExtra(CandidateActionReceiver.EXTRA_EVENT_ID, eventId)
            .putExtra(CandidateActionReceiver.EXTRA_DELAY_MINUTES, delayMinutes);
        return PendingIntent.getBroadcast(
            context,
            requestCode,
            action,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
    }

    private static String compactTime(String value) {
        if (value == null || value.isEmpty()) return "";
        String normalized = value.replace('T', ' ');
        return normalized.length() >= 16 ? normalized.substring(0, 16) : normalized;
    }

    static int stableNotificationId(String eventId) {
        int value = eventId.hashCode() & 0x7fffffff;
        return value == 0 ? 1 : value;
    }
}
