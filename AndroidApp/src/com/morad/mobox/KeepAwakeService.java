package com.morad.mobox;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.util.Log;

import java.io.BufferedReader;
import java.io.FileReader;

/**
 * Prevents the Mi Box 4 (Android 9 / Amlogic) from entering deep-sleep coma when
 * the TV sends HDMI-CEC <Standby>, and wakes the screen immediately when HDMI
 * Hot-Plug Detect (HPD) returns (0 -> 1) as the TV turns back on.
 */
public class KeepAwakeService extends Service {
    private static final String TAG = "MoBoxWakeGuard";
    private static final String CHANNEL_ID = "mobox_wake_guard";
    private static final int NOTIF_ID = 1001;
    private static final String HPD_PATH = "/sys/class/amhdmitx/amhdmitx0/hpd_state";

    private PowerManager powerManager;
    private PowerManager.WakeLock partialLock;
    private Handler handler;
    private int lastHpd = -1;
    private boolean running = false;

    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (intent == null || intent.getAction() == null) return;
            String action = intent.getAction();
            if ("android.intent.action.HDMI_PLUGGED".equals(action)) {
                boolean plugged = intent.getBooleanExtra("state", false);
                Log.i(TAG, "HDMI_PLUGGED state=" + plugged);
                lastHpd = plugged ? 1 : 0;
                if (plugged) {
                    wakeDisplay("HDMI_PLUGGED");
                }
            } else if (Intent.ACTION_SCREEN_OFF.equals(action)) {
                Log.i(TAG, "SCREEN_OFF observed; keeping CPU awake for instant TV wake");
                lastHpd = readHpdState();
            }
        }
    };

    private final Runnable hpdPoll = new Runnable() {
        @Override
        public void run() {
            if (!running) return;
            try {
                int hpd = readHpdState();
                if (hpd == 1 && lastHpd == 0) {
                    Log.i(TAG, "HDMI HPD 0 -> 1 detected (TV turned on)");
                    wakeDisplay("HPD_RISING_EDGE");
                }
                if (hpd != -1) {
                    lastHpd = hpd;
                }
            } catch (Throwable ignored) {
            }
            if (running && handler != null) {
                handler.postDelayed(this, 2000L);
            }
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        powerManager = (PowerManager) getSystemService(POWER_SERVICE);
        handler = new Handler(Looper.getMainLooper());
        startForegroundCompat();
        acquirePartialLock();

        IntentFilter filter = new IntentFilter();
        filter.addAction("android.intent.action.HDMI_PLUGGED");
        filter.addAction(Intent.ACTION_SCREEN_OFF);
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(receiver, filter, Context.RECEIVER_EXPORTED);
        } else {
            registerReceiver(receiver, filter);
        }

        lastHpd = readHpdState();
        running = true;
        handler.postDelayed(hpdPoll, 2000L);
        Log.i(TAG, "KeepAwakeService started; initial hpd=" + lastHpd);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        acquirePartialLock();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        running = false;
        if (handler != null) handler.removeCallbacks(hpdPoll);
        try {
            unregisterReceiver(receiver);
        } catch (Throwable ignored) {
        }
        if (partialLock != null && partialLock.isHeld()) {
            try {
                partialLock.release();
            } catch (Throwable ignored) {
            }
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void startForegroundCompat() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(
                    CHANNEL_ID,
                    "MoBox TV Auto-Wake",
                    NotificationManager.IMPORTANCE_MIN
            );
            ch.setShowBadge(false);
            NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (nm != null) nm.createNotificationChannel(ch);
            Notification n = new Notification.Builder(this, CHANNEL_ID)
                    .setContentTitle("MoBox TV Auto-Wake")
                    .setContentText("Ready for TV power-on")
                    .setSmallIcon(android.R.drawable.ic_lock_idle_charging)
                    .setOngoing(true)
                    .build();
            startForeground(NOTIF_ID, n);
        } else {
            Notification n = new Notification.Builder(this)
                    .setContentTitle("MoBox TV Auto-Wake")
                    .setSmallIcon(android.R.drawable.ic_lock_idle_charging)
                    .setOngoing(true)
                    .build();
            startForeground(NOTIF_ID, n);
        }
    }

    private void acquirePartialLock() {
        if (powerManager == null) return;
        if (partialLock == null) {
            partialLock = powerManager.newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK,
                    "MoBox:NoDeepSleep"
            );
            partialLock.setReferenceCounted(false);
        }
        if (!partialLock.isHeld()) {
            partialLock.acquire();
        }
    }

    @SuppressWarnings("deprecation")
    private void wakeDisplay(String reason) {
        if (powerManager == null) return;
        try {
            if (!powerManager.isInteractive()) {
                Log.i(TAG, "Waking display (" + reason + ")");
                PowerManager.WakeLock wl = powerManager.newWakeLock(
                        PowerManager.FULL_WAKE_LOCK
                                | PowerManager.ACQUIRE_CAUSES_WAKEUP
                                | PowerManager.ON_AFTER_RELEASE,
                        "MoBox:TvWake"
                );
                wl.acquire(4000L);
            }
        } catch (Throwable t) {
            Log.w(TAG, "wakeDisplay failed: " + t.getMessage());
        }
    }

    private static int readHpdState() {
        try (BufferedReader br = new BufferedReader(new FileReader(HPD_PATH))) {
            String line = br.readLine();
            if (line != null) {
                line = line.trim();
                if (line.startsWith("1")) return 1;
                if (line.startsWith("0")) return 0;
            }
        } catch (Throwable ignored) {
        }
        return -1;
    }

    public static void ensureStarted(Context ctx) {
        Intent i = new Intent(ctx, KeepAwakeService.class);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ctx.startForegroundService(i);
            } else {
                ctx.startService(i);
            }
        } catch (Throwable ignored) {
        }
    }
}
