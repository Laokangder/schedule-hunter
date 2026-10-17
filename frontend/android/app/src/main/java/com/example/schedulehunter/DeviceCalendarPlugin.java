package com.example.schedulehunter;

import android.Manifest;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.database.Cursor;
import android.net.Uri;
import android.provider.CalendarContract;

import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

@CapacitorPlugin(
    name = "DeviceCalendar",
    permissions = @Permission(
        alias = "calendar",
        strings = { Manifest.permission.READ_CALENDAR, Manifest.permission.WRITE_CALENDAR }
    )
)
public class DeviceCalendarPlugin extends Plugin {
    @PluginMethod
    public void checkCalendarPermission(PluginCall call) {
        resolvePermission(call);
    }

    @PluginMethod
    public void requestCalendarPermission(PluginCall call) {
        if (getPermissionState("calendar") == PermissionState.GRANTED) {
            resolvePermission(call);
            return;
        }
        requestPermissionForAlias("calendar", call, "calendarPermissionCallback");
    }

    @PermissionCallback
    private void calendarPermissionCallback(PluginCall call) {
        resolvePermission(call);
    }

    @PluginMethod
    public void upsertEvent(PluginCall call) {
        if (!ensurePermission(call)) return;

        String title = call.getString("title", "日程");
        String startValue = call.getString("startTime", "");
        String endValue = call.getString("endTime", startValue);
        long startTime;
        long endTime;
        try {
            startTime = parseTime(startValue);
            endTime = parseTime(endValue);
        } catch (ParseException error) {
            call.reject("日程时间格式无效");
            return;
        }
        if (endTime <= startTime) endTime = startTime + 60 * 60 * 1000L;

        ContentResolver resolver = getContext().getContentResolver();
        long calendarId = findWritableCalendar(resolver);
        if (calendarId < 0) {
            call.reject("手机中没有可写入的系统日历");
            return;
        }

        ContentValues values = new ContentValues();
        values.put(CalendarContract.Events.CALENDAR_ID, calendarId);
        values.put(CalendarContract.Events.TITLE, title);
        values.put(CalendarContract.Events.DTSTART, startTime);
        values.put(CalendarContract.Events.DTEND, endTime);
        values.put(CalendarContract.Events.EVENT_TIMEZONE, "Asia/Shanghai");
        values.put(CalendarContract.Events.EVENT_LOCATION, call.getString("location", ""));
        values.put(CalendarContract.Events.DESCRIPTION, call.getString("description", "由日程猎人同步"));

        try {
            String eventId = call.getString("eventId", "");
            Uri eventUri;
            if (!eventId.isEmpty()) {
                eventUri = ContentUris.withAppendedId(CalendarContract.Events.CONTENT_URI, Long.parseLong(eventId));
                int updated = resolver.update(eventUri, values, null, null);
                if (updated == 0) eventUri = resolver.insert(CalendarContract.Events.CONTENT_URI, values);
            } else {
                eventUri = resolver.insert(CalendarContract.Events.CONTENT_URI, values);
            }
            if (eventUri == null) {
                call.reject("系统日历写入失败");
                return;
            }
            JSObject result = new JSObject();
            result.put("eventId", eventUri.getLastPathSegment());
            result.put("synced", true);
            call.resolve(result);
        } catch (Exception error) {
            call.reject("系统日历写入失败", error);
        }
    }

    @PluginMethod
    public void deleteEvent(PluginCall call) {
        if (!ensurePermission(call)) return;
        String eventId = call.getString("eventId", "");
        if (eventId.isEmpty()) {
            JSObject result = new JSObject();
            result.put("deleted", false);
            call.resolve(result);
            return;
        }
        try {
            Uri uri = ContentUris.withAppendedId(CalendarContract.Events.CONTENT_URI, Long.parseLong(eventId));
            int deleted = getContext().getContentResolver().delete(uri, null, null);
            JSObject result = new JSObject();
            result.put("deleted", deleted > 0);
            call.resolve(result);
        } catch (Exception error) {
            call.reject("删除系统日历事件失败", error);
        }
    }

    private void resolvePermission(PluginCall call) {
        JSObject result = new JSObject();
        result.put("supported", true);
        result.put("granted", getPermissionState("calendar") == PermissionState.GRANTED);
        call.resolve(result);
    }

    private boolean ensurePermission(PluginCall call) {
        if (getPermissionState("calendar") == PermissionState.GRANTED) return true;
        call.reject("尚未获得系统日历权限");
        return false;
    }

    private long findWritableCalendar(ContentResolver resolver) {
        String[] projection = { CalendarContract.Calendars._ID, CalendarContract.Calendars.CALENDAR_ACCESS_LEVEL };
        String selection = CalendarContract.Calendars.VISIBLE + "=1 AND "
            + CalendarContract.Calendars.CALENDAR_ACCESS_LEVEL + ">=?";
        String[] args = { String.valueOf(CalendarContract.Calendars.CAL_ACCESS_CONTRIBUTOR) };
        try (Cursor cursor = resolver.query(CalendarContract.Calendars.CONTENT_URI, projection, selection, args, null)) {
            if (cursor != null && cursor.moveToFirst()) return cursor.getLong(0);
        }
        return -1;
    }

    private long parseTime(String value) throws ParseException {
        String[] patterns = {
            "yyyy-MM-dd'T'HH:mm:ssXXX",
            "yyyy-MM-dd'T'HH:mmXXX",
            "yyyy-MM-dd'T'HH:mm:ss",
            "yyyy-MM-dd'T'HH:mm"
        };
        for (String pattern : patterns) {
            try {
                SimpleDateFormat format = new SimpleDateFormat(pattern, Locale.US);
                format.setLenient(false);
                format.setTimeZone(TimeZone.getTimeZone("Asia/Shanghai"));
                Date date = format.parse(value);
                if (date != null) return date.getTime();
            } catch (ParseException ignored) {}
        }
        throw new ParseException("Unsupported date", 0);
    }
}
