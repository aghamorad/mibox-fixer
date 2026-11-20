package com.morad.mobox;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.DisplayMetrics;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;

import java.net.DatagramPacket;
import java.net.DatagramSocket;

/**
 * Lightweight 60Hz Air Mouse / Trackpad receiver on UDP port 8766.
 * Renders a crisp high-contrast cursor overlay and injects clicks/scrolls
 * via AccessibilityService.dispatchGesture (no root required).
 */
public class PointerService extends AccessibilityService {

    public static final int UDP_PORT = 8766;

    private WindowManager wm;
    private CursorView cursorView;
    private WindowManager.LayoutParams lp;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private DatagramSocket socket;
    private volatile boolean running = false;

    private int screenW = 1920;
    private int screenH = 1080;
    private float curX = 960f;
    private float curY = 540f;
    private long lastMoveMs = 0L;

    private final Runnable hideTask = () -> {
        if (cursorView != null) {
            cursorView.setVisibility(View.GONE);
        }
    };

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
        DisplayMetrics dm = new DisplayMetrics();
        wm.getDefaultDisplay().getRealMetrics(dm);
        screenW = Math.max(dm.widthPixels, 640);
        screenH = Math.max(dm.heightPixels, 480);
        curX = screenW / 2f;
        curY = screenH / 2f;

        cursorView = new CursorView(this);
        cursorView.setVisibility(View.GONE);

        int overlayType = Build.VERSION.SDK_INT >= 22
            ? WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY
            : WindowManager.LayoutParams.TYPE_SYSTEM_ALERT;

        lp = new WindowManager.LayoutParams(
            dp(28), dp(28),
            overlayType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        );
        lp.gravity = Gravity.TOP | Gravity.START;
        lp.x = Math.round(curX);
        lp.y = Math.round(curY);
        wm.addView(cursorView, lp);

        startUdpListener();
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // Unused; we only inject gestures and draw the cursor overlay.
    }

    @Override
    public void onInterrupt() {}

    @Override
    public void onDestroy() {
        running = false;
        if (socket != null) {
            socket.close();
            socket = null;
        }
        if (wm != null && cursorView != null) {
            try { wm.removeView(cursorView); } catch (Exception ignored) {}
        }
        super.onDestroy();
    }

    private void startUdpListener() {
        running = true;
        new Thread(() -> {
            try {
                socket = new DatagramSocket(UDP_PORT);
                byte[] buf = new byte[256];
                while (running) {
                    DatagramPacket pkt = new DatagramPacket(buf, buf.length);
                    socket.receive(pkt);
                    String msg = new String(pkt.getData(), 0, pkt.getLength(), "UTF-8").trim();
                    handleCommand(msg);
                }
            } catch (Exception ignored) {}
        }, "MoBoxPointerUDP").start();
    }

    private void handleCommand(String msg) {
        if (msg.isEmpty()) return;
        String[] parts = msg.split("\\s+");
        String cmd = parts[0];
        if ("M".equals(cmd) && parts.length >= 3) {
            try {
                float dx = Float.parseFloat(parts[1]);
                float dy = Float.parseFloat(parts[2]);
                mainHandler.post(() -> moveCursor(dx, dy));
            } catch (NumberFormatException ignored) {}
        } else if ("C".equals(cmd)) {
            mainHandler.post(this::performClickAtCursor);
        } else if ("R".equals(cmd)) {
            mainHandler.post(() -> performGlobalAction(GLOBAL_ACTION_BACK));
        } else if ("S".equals(cmd) && parts.length >= 2) {
            try {
                float dy = Float.parseFloat(parts[1]);
                mainHandler.post(() -> performScrollAtCursor(dy));
            } catch (NumberFormatException ignored) {}
        } else if ("CENTER".equals(cmd)) {
            mainHandler.post(() -> {
                curX = screenW / 2f;
                curY = screenH / 2f;
                moveCursor(0f, 0f);
            });
        }
    }

    private void moveCursor(float dx, float dy) {
        curX = Math.max(0f, Math.min(screenW - 4f, curX + dx));
        curY = Math.max(0f, Math.min(screenH - 4f, curY + dy));
        if (cursorView != null && wm != null && lp != null) {
            if (cursorView.getVisibility() != View.VISIBLE) {
                cursorView.setVisibility(View.VISIBLE);
            }
            lp.x = Math.round(curX);
            lp.y = Math.round(curY);
            wm.updateViewLayout(cursorView, lp);
            mainHandler.removeCallbacks(hideTask);
            mainHandler.postDelayed(hideTask, 8000);
        }
    }

    private void performClickAtCursor() {
        if (Build.VERSION.SDK_INT < 24) return;
        Path p = new Path();
        p.moveTo(curX, curY);
        GestureDescription.StrokeDescription stroke =
            new GestureDescription.StrokeDescription(p, 0, 50);
        dispatchGesture(new GestureDescription.Builder().addStroke(stroke).build(), null, null);
    }

    private void performScrollAtCursor(float dy) {
        if (Build.VERSION.SDK_INT < 24) return;
        float startY = Math.max(60f, Math.min(screenH - 60f, curY));
        float endY = Math.max(40f, Math.min(screenH - 40f, startY - dy * 4f));
        Path p = new Path();
        p.moveTo(curX, startY);
        p.lineTo(curX, endY);
        GestureDescription.StrokeDescription stroke =
            new GestureDescription.StrokeDescription(p, 0, 140);
        dispatchGesture(new GestureDescription.Builder().addStroke(stroke).build(), null, null);
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}
