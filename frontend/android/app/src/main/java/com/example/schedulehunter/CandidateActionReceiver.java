package com.example.schedulehunter;

import android.app.AlarmManager;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

import org.json.JSONArray;
import org.json.JSONObject;

public class CandidateActionReceiver extends BroadcastReceiver {
    static final String ACTION_SNOOZE = "com.example.schedulehunter.CANDIDATE_SNOOZE";
    static final String ACTION_IGNORE = "com.example.schedulehunter.CANDIDATE_IGNORE";
    static final String ACTION_RESHOW = "com.example.schedulehunter.CANDIDATE_RESHOW";
    static final String ACTION_OPEN = "com.example.schedulehunter.CANDIDATE_OPEN";
    static final String EXTRA_EVENT_ID = "event_id";
    static final String EXTRA_DELAY_MINUTES = "delay_minutes";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) return;
        String eventId = intent.getStringExtra(EXTRA_EVENT_ID);
        if (eventId == null || eventId.isEmpty()) return;

        String action = intent.getAction();
        int notificationId = BackgroundCandidateProcessor.stableNotificationId(eventId);
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);

        if (ACTION_OPEN.equals(action)) {
            if (manager != null) manager.cancel(notificationId);
            Intent openIntent = new Intent(context, MainActivity.class)
                .putExtra("captured_event_id", eventId)
                .putExtra("candidate_action", "confirm")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            context.startActivity(openIntent);
            return;
        }

        if (ACTION_IGNORE.equals(action)) {
            BackgroundCandidateProcessor.syncCandidateAction(context, eventId, "ignored", 0);
            NotificationCaptureStore.acknowledge(context, new JSONArray().put(eventId));
            if (manager != null) manager.cancel(notificationId);
            return;
        }

        if (ACTION_SNOOZE.equals(action)) {
            long delayMinutes = Math.max(1, intent.getIntExtra(EXTRA_DELAY_MINUTES, 10));
            BackgroundCandidateProcessor.syncCandidateAction(context, eventId, "snooze", (int) delayMinutes);
            long triggerAt = System.currentTimeMillis() + delayMinutes * 60_000L;
            NotificationCaptureStore.markSnoozed(context, eventId, triggerAt);
            if (manager != null) manager.cancel(notificationId);

            Intent alarmIntent = new Intent(context, CandidateActionReceiver.class)
                .setAction(ACTION_RESHOW)
                .putExtra(EXTRA_EVENT_ID, eventId);
            PendingIntent pendingIntent = PendingIntent.getBroadcast(
                context,
                notificationId ^ (int) delayMinutes,
                alarmIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );
            AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            if (alarmManager != null) {
                alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pendingIntent);
            }
            return;
        }

        if (ACTION_RESHOW.equals(action)) {
            JSONObject event = NotificationCaptureStore.getEvent(context, eventId);
            JSONObject response = event == null ? null : event.optJSONObject("parsed_response");
            if (event != null && response != null) {
                NotificationCaptureStore.markSnoozed(context, eventId, 0L);
                BackgroundCandidateProcessor.showCandidateNotification(context, event, response);
            }
        }
    }
}
