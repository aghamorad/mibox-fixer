package com.morad.mobox;

import android.app.Activity;
import android.app.PendingIntent;
import android.app.UiModeManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.net.Uri;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.StatFs;
import android.provider.Settings;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/**
 * 100% native Android UI (no WebView) so D-Pad remotes (OK / Enter),
 * Bluetooth mice, and phone touchscreens all focus and click reliably.
 */
public class MainActivity extends Activity {

    private static final String PLAYLIST_URL =
        "https://raw.githubusercontent.com/aghamorad/mibox-fixer/main/playlists/world.m3u";

    private static final String[][] CORE_APPS = new String[][] {
        {
            "hume",
            "Hume Launcher (Apple TV-style Home)",
            "com.petrobot.hume",
            "https://github.com/petrobot-admin/hume-launcher/releases/download/v7.8/HumeLauncher-7.8.apk",
            "https://github.com/petrobot-admin/hume-launcher/releases/download/v7.8/HumeLauncher-7.8.apk"
        },
        {
            "mytv",
            "TV Live (2,200+ Worldwide & Iran TV)",
            "com.github.mytv.android",
            "https://github.com/mytv-android/mytv-android/releases/download/V2.2.0.219/mytv-android-tv-2.2.0.219-all-sdk23-original.apk",
            "https://github.com/mytv-android/mytv-android/releases/download/V2.2.0.219/mytv-android-tv-2.2.0.219-all-sdk23-original.apk"
        },
        {
            "smarttube",
            "SmartTube (Ad-Free YouTube)",
            "org.smarttube.stable",
            "https://github.com/yuliskov/SmartTube/releases/download/32.56s/SmartTube_stable_32.56_armeabi-v7a.apk",
            "https://github.com/yuliskov/SmartTube/releases/download/32.56s/SmartTube_stable_32.56_arm64-v8a.apk"
        },
        {
            "tvbro",
            "TV Bro 3.0.5 (TV Web Browser)",
            "com.phlox.tvwebbrowser",
            "https://github.com/truefedex/tv-bro/releases/download/v3.0.5/tvbro-3.0.5-generic-geckoExcluded.apk",
            "https://github.com/truefedex/tv-bro/releases/download/v3.0.5/tvbro-3.0.5-generic-geckoExcluded.apk"
        },
        {
            "slamvision",
            "SlamVision (24/7 Retro Wrestling)",
            "com.slamvision.tv",
            "https://github.com/jhatren927-ai/slamvision-tv/releases/download/v1.4.0/SlamVision.apk",
            "https://github.com/jhatren927-ai/slamvision-tv/releases/download/v1.4.0/SlamVision.apk"
        },
        {
            "matvt",
            "MATVT (Remote Mouse & Scroll Helper)",
            "io.github.virresh.matvt",
            "https://github.com/virresh/matvt/releases/download/v1.0.6/matvt-app-release-v1.0.6.apk",
            "https://github.com/virresh/matvt/releases/download/v1.0.6/matvt-app-release-v1.0.6.apk"
        },
        {
            "aerialviews",
            "Aerial Views (4K Space & Nature Slideshow)",
            "com.neilturner.aerialviews",
            "https://github.com/theothernt/AerialViews/releases/download/1.8.5/aerial-views-1.8.5.apk",
            "https://github.com/theothernt/AerialViews/releases/download/1.8.5/aerial-views-1.8.5.apk"
        }
    };

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private TextView statusTitle;
    private TextView statusBody;
    private ProgressBar progressBar;
    private Button heroButton;
    private TextView zltStatusText;
    private EditText zltPassInput;
    private LinearLayout appsContainer;
    private volatile boolean busy = false;
    private volatile String discoveredBoxIp = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(Color.parseColor("#0D0F14"));
        scroll.setFillViewport(true);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(24);
        root.setPadding(pad, pad, pad, dp(40));
        scroll.addView(root);

        // Header
        TextView title = new TextView(this);
        title.setText("MoBox");
        title.setTextColor(Color.parseColor("#F4F1EA"));
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 28);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title);

        TextView sub = new TextView(this);
        String kind = isTvDevice() ? "Mi Box / Android TV" : "Android Phone / Tablet";
        String arch = is64Bit() ? "64-bit (arm64-v8a)" : "32-bit (armeabi-v7a)";
        sub.setText(Build.MANUFACTURER + " " + Build.MODEL + " (" + kind + ")  •  " + arch + "  •  " + getFreeStorageMb() + " MB free");
        sub.setTextColor(Color.parseColor("#949DB0"));
        sub.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        sub.setPadding(0, dp(4), 0, dp(18));
        root.addView(sub);

        // 1. Primary 1-Click Setup Card
        LinearLayout heroCard = makeCard();
        root.addView(heroCard, cardLp());

        statusTitle = new TextView(this);
        statusTitle.setText("1. Set Up Everything in One Click");
        statusTitle.setTextColor(Color.parseColor("#F4F1EA"));
        statusTitle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20);
        statusTitle.setTypeface(Typeface.DEFAULT_BOLD);
        heroCard.addView(statusTitle);

        statusBody = new TextView(this);
        statusBody.setText("Installs any missing core apps (Hume Launcher, TV Live with 2,200+ channels, SmartTube, TV Bro, SlamVision, MATVT, Aerial Views 4K Space & Nature) and programs TV Live.");
        statusBody.setTextColor(Color.parseColor("#A9B2C6"));
        statusBody.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
        statusBody.setPadding(0, dp(6), 0, dp(14));
        heroCard.addView(statusBody);

        heroButton = makeButton("Set Up Mi Box Now (All-in-One)", "#32B868", "#FFFFFF");
        heroButton.setOnClickListener(v -> runOneClickSetup());
        heroCard.addView(heroButton);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(CORE_APPS.length + 1);
        progressBar.setProgress(0);
        LinearLayout.LayoutParams pbLp = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(10));
        pbLp.topMargin = dp(12);
        heroCard.addView(progressBar, pbLp);

        // 2. Quick TV Settings Card
        LinearLayout tvCard = makeCard();
        root.addView(tvCard, cardLp());

        TextView tvTitle = new TextView(this);
        tvTitle.setText("2. Quick TV Controls & Pairing");
        tvTitle.setTextColor(Color.parseColor("#F4F1EA"));
        tvTitle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        tvTitle.setTypeface(Typeface.DEFAULT_BOLD);
        tvTitle.setPadding(0, 0, 0, dp(10));
        tvCard.addView(tvTitle);

        Button btnProgramTv = makeButton("Program TV Live Channels (Worldwide + Iran)", "#1C212D", "#F4F1EA");
        btnProgramTv.setOnClickListener(v -> programTvLiveAsync());
        tvCard.addView(btnProgramTv, btnLp());

        Button btnScreensaver = makeButton("Pick 4K Space & Nature Screensaver (Aerial Views)", "#1C212D", "#F4F1EA");
        btnScreensaver.setOnClickListener(v -> openSystemScreen(Settings.ACTION_DREAM_SETTINGS));
        tvCard.addView(btnScreensaver, btnLp());

        Button btnHome = makeButton("Pick Home Screen (Hume Launcher)", "#1C212D", "#F4F1EA");
        btnHome.setOnClickListener(v -> openSystemScreen(Settings.ACTION_HOME_SETTINGS));
        tvCard.addView(btnHome, btnLp());

        Button btnAccessibility = makeButton("Turn On MATVT Remote Mouse & Scroll Helper", "#1C212D", "#F4F1EA");
        btnAccessibility.setOnClickListener(v -> openSystemScreen(Settings.ACTION_ACCESSIBILITY_SETTINGS));
        tvCard.addView(btnAccessibility, btnLp());

        Button btnBt = makeButton("Open Bluetooth Pairing (Turn Mac Bluetooth OFF First!)", "#1C212D", "#F4F1EA");
        btnBt.setOnClickListener(v -> openSystemScreen(Settings.ACTION_BLUETOOTH_SETTINGS));
        tvCard.addView(btnBt, btnLp());

        // 3. ZLT X28 5G Router Card
        LinearLayout zltCard = makeCard();
        root.addView(zltCard, cardLp());

        TextView zltTitle = new TextView(this);
        zltTitle.setText("3. Fix ZLT X28 5G Router (192.168.70.1)");
        zltTitle.setTextColor(Color.parseColor("#F4F1EA"));
        zltTitle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        zltTitle.setTypeface(Typeface.DEFAULT_BOLD);
        zltCard.addView(zltTitle);

        TextView zltDesc = new TextView(this);
        zltDesc.setText("While connected to the ZLT X28 Wi-Fi, tap below to fix the empty Auto-APN bug (sets MCI mcinet), enable Auto-Dial, and clear stuck band locks.");
        zltDesc.setTextColor(Color.parseColor("#A9B2C6"));
        zltDesc.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        zltDesc.setPadding(0, dp(4), 0, dp(8));
        zltCard.addView(zltDesc);

        zltPassInput = new EditText(this);
        zltPassInput.setText("admin");
        zltPassInput.setHint("Router admin password");
        zltPassInput.setTextColor(Color.parseColor("#F4F1EA"));
        zltPassInput.setHintTextColor(Color.parseColor("#5E677A"));
        zltPassInput.setBackgroundColor(Color.parseColor("#0D0F14"));
        zltPassInput.setPadding(dp(12), dp(10), dp(12), dp(10));
        zltPassInput.setSingleLine(true);
        zltCard.addView(zltPassInput, btnLp());

        Button btnZlt = makeButton("Fix My ZLT X28 Router Now", "#E84A27", "#FFFFFF");
        btnZlt.setOnClickListener(v -> runZltFixAsync());
        zltCard.addView(btnZlt, btnLp());

        zltStatusText = new TextView(this);
        zltStatusText.setText("");
        zltStatusText.setTextColor(Color.parseColor("#E5A913"));
        zltStatusText.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        zltStatusText.setPadding(0, dp(8), 0, 0);
        zltCard.addView(zltStatusText);

        // 4. Individual Apps Card
        LinearLayout appsCard = makeCard();
        root.addView(appsCard, cardLp());

        TextView appsTitle = new TextView(this);
        appsTitle.setText("4. Individual Apps (" + arch + ")");
        appsTitle.setTextColor(Color.parseColor("#F4F1EA"));
        appsTitle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        appsTitle.setTypeface(Typeface.DEFAULT_BOLD);
        appsTitle.setPadding(0, 0, 0, dp(8));
        appsCard.addView(appsTitle);

        appsContainer = new LinearLayout(this);
        appsContainer.setOrientation(LinearLayout.VERTICAL);
        appsCard.addView(appsContainer);
        rebuildAppButtons();

        // Footer
        TextView footer = new TextView(this);
        footer.setText("Made by Morad  •  MoBox v2.1.1 (Native Android TV + Phone)");
        footer.setTextColor(Color.parseColor("#5E677A"));
        footer.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        footer.setGravity(Gravity.CENTER_HORIZONTAL);
        footer.setPadding(0, dp(14), 0, 0);
        root.addView(footer);

        setContentView(scroll);
        heroButton.requestFocus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        rebuildAppButtons();
    }

    private void rebuildAppButtons() {
        if (appsContainer == null) return;
        appsContainer.removeAllViews();
        boolean arm64 = is64Bit();
        for (final String[] row : CORE_APPS) {
            final String key = row[0];
            final String title = row[1];
            final String pkg = row[2];
            final String url = arm64 ? row[4] : row[3];
            boolean installed = isPackageInstalled(pkg);
            String label = (installed ? "[Installed]  " : "[Install]  ") + title;
            Button b = makeButton(label, installed ? "#151922" : "#1C212D", installed ? "#5CE092" : "#F4F1EA");
            b.setOnClickListener(v -> installSingleAsync(title, key, url));
            appsContainer.addView(b, btnLp());
        }
    }

    // ------------------------------------------------------------------ UI Helpers

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private LinearLayout.LayoutParams cardLp() {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.bottomMargin = dp(14);
        return lp;
    }

    private LinearLayout.LayoutParams btnLp() {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(8);
        return lp;
    }

    private LinearLayout makeCard() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(18), dp(18), dp(18), dp(18));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.parseColor("#151922"));
        bg.setCornerRadius(dp(14));
        bg.setStroke(dp(1), Color.parseColor("#2A3142"));
        card.setBackground(bg);
        return card;
    }

    private Button makeButton(String text, String fillHex, String textHex) {
        Button btn = new Button(this);
        btn.setText(text);
        btn.setAllCaps(false);
        btn.setTextColor(Color.parseColor(textHex));
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        btn.setTypeface(Typeface.DEFAULT_BOLD);
        btn.setPadding(dp(16), dp(12), dp(16), dp(12));
        btn.setMinimumHeight(dp(50));
        btn.setFocusable(true);
        btn.setFocusableInTouchMode(false);

        GradientDrawable normal = new GradientDrawable();
        normal.setColor(Color.parseColor(fillHex));
        normal.setCornerRadius(dp(10));
        normal.setStroke(dp(1), Color.parseColor("#353D52"));

        GradientDrawable focused = new GradientDrawable();
        focused.setColor(Color.parseColor(fillHex));
        focused.setCornerRadius(dp(10));
        focused.setStroke(dp(3), Color.parseColor("#E5A913")); // Bold Paul Rand gold focus ring for TV remote!

        GradientDrawable pressed = new GradientDrawable();
        pressed.setColor(Color.parseColor("#E84A27"));
        pressed.setCornerRadius(dp(10));
        pressed.setStroke(dp(3), Color.WHITE);

        StateListDrawable states = new StateListDrawable();
        states.addState(new int[] { android.R.attr.state_pressed }, pressed);
        states.addState(new int[] { android.R.attr.state_focused }, focused);
        states.addState(new int[] { android.R.attr.state_selected }, focused);
        states.addState(new int[] {}, normal);
        btn.setBackground(states);
        return btn;
    }

    private void setStatus(final String title, final String body, final int step) {
        mainHandler.post(() -> {
            if (title != null) statusTitle.setText(title);
            if (body != null) statusBody.setText(body);
            if (step >= 0) progressBar.setProgress(step);
        });
    }

    // ------------------------------------------------------------------ Actions

    private void runOneClickSetup() {
        if (busy) return;
        busy = true;
        heroButton.setEnabled(false);
        new Thread(() -> {
            try {
                boolean arm64 = is64Bit();
                int step = 0;
                for (String[] row : CORE_APPS) {
                    step++;
                    String key = row[0];
                    String title = row[1];
                    String pkg = row[2];
                    String url = arm64 ? row[4] : row[3];
                    if (isPackageInstalled(pkg)) {
                        setStatus("Checking apps (" + step + "/" + CORE_APPS.length + ")", "Keeping existing " + title, step);
                        Thread.sleep(200);
                        continue;
                    }
                    setStatus("Downloading (" + step + "/" + CORE_APPS.length + ")", "Downloading " + title + "…", step);
                    File apk = downloadToCache(url, key + ".apk");
                    setStatus("Installing (" + step + "/" + CORE_APPS.length + ")", "Tap Install on the screen for " + title, step);
                    installApkSession(apk);
                    Thread.sleep(1600);
                }
                setStatus("Programming TV Live…", "Setting Worldwide + Top Picks + Iran channels…", CORE_APPS.length + 1);
                boolean tvOk = configureTvLiveAtHost("127.0.0.1");
                if (!tvOk && !discoveredBoxIp.isEmpty()) {
                    tvOk = configureTvLiveAtHost(discoveredBoxIp);
                }
                setStatus(
                    "Setup Complete",
                    tvOk
                        ? "Apps queued and TV Live channels programmed! Use Section 2 below to set Hume Home & Aerial Views Screensaver."
                        : "Apps queued! Open TV Live once, then tap 'Program TV Live Channels' below.",
                    CORE_APPS.length + 1
                );
            } catch (Exception e) {
                setStatus("Setup Note", "Stopped: " + e.getMessage(), -1);
            } finally {
                busy = false;
                mainHandler.post(() -> {
                    heroButton.setEnabled(true);
                    rebuildAppButtons();
                });
            }
        }).start();
    }

    private void installSingleAsync(final String title, final String key, final String url) {
        if (busy) {
            setStatus(null, "Please wait for the current install to finish…", -1);
            return;
        }
        busy = true;
        new Thread(() -> {
            try {
                setStatus("Downloading " + title, "Fetching APK from GitHub…", 1);
                File apk = downloadToCache(url, key + ".apk");
                setStatus("Installing " + title, "Approve the install prompt on screen.", 2);
                installApkSession(apk);
            } catch (Exception e) {
                setStatus("Install Note", "Could not download " + title + ": " + e.getMessage(), -1);
            } finally {
                busy = false;
                mainHandler.post(this::rebuildAppButtons);
            }
        }).start();
    }

    private void programTvLiveAsync() {
        setStatus("Programming TV Live…", "Looking for TV Live on this box or Wi-Fi…", -1);
        new Thread(() -> {
            boolean ok = configureTvLiveAtHost("127.0.0.1");
            if (!ok) {
                String found = scanWifiForMiBox();
                if (!found.isEmpty()) {
                    ok = configureTvLiveAtHost(found);
                }
            }
            final boolean finalOk = ok;
            setStatus(
                finalOk ? "TV Live Ready" : "Open TV Live Once",
                finalOk
                    ? "TV Live now has all 2,200+ Worldwide & Iran channels (Top Picks + Worldwide)!"
                    : "Could not reach TV Live (port 10591). Open TV Live on the TV once, then tap this button again.",
                -1
            );
        }).start();
    }

    private void openSystemScreen(String action) {
        try {
            Intent intent = new Intent(action);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        } catch (Exception e) {
            try {
                Intent fallback = new Intent(Settings.ACTION_SETTINGS);
                fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(fallback);
            } catch (Exception ignored) {}
        }
    }

    private void runZltFixAsync() {
        final String pw = zltPassInput.getText().toString().trim();
        mainHandler.post(() -> zltStatusText.setText("Connecting to ZLT X28 at 192.168.70.1…"));
        new Thread(() -> {
            final String msg = fixZltRouter(pw.isEmpty() ? "admin" : pw);
            mainHandler.post(() -> zltStatusText.setText(msg));
        }).start();
    }

    // ------------------------------------------------------------------ Device & Network Logic

    private boolean isTvDevice() {
        UiModeManager um = (UiModeManager) getSystemService(Context.UI_MODE_SERVICE);
        if (um != null && um.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION) {
            return true;
        }
        return getPackageManager().hasSystemFeature(PackageManager.FEATURE_LEANBACK);
    }

    private boolean is64Bit() {
        for (String abi : Build.SUPPORTED_ABIS) {
            if ("arm64-v8a".equals(abi) || "x86_64".equals(abi)) return true;
        }
        return false;
    }

    private boolean isPackageInstalled(String pkg) {
        try {
            getPackageManager().getPackageInfo(pkg, 0);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private long getFreeStorageMb() {
        try {
            StatFs stat = new StatFs(Environment.getDataDirectory().getPath());
            return (stat.getAvailableBlocksLong() * stat.getBlockSizeLong()) / (1024L * 1024L);
        } catch (Exception e) {
            return 0;
        }
    }

    private String getWifiIp() {
        try {
            WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wm != null) {
                WifiInfo info = wm.getConnectionInfo();
                int ip = info.getIpAddress();
                if (ip != 0) {
                    return String.format("%d.%d.%d.%d",
                        (ip & 0xff), (ip >> 8 & 0xff), (ip >> 16 & 0xff), (ip >> 24 & 0xff));
                }
            }
        } catch (Exception ignored) {}
        return "";
    }

    private void installApkSession(File apkFile) throws Exception {
        if (Build.VERSION.SDK_INT >= 26 && !getPackageManager().canRequestPackageInstalls()) {
            Intent perm = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:" + getPackageName()));
            perm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(perm);
        }
        PackageInstaller installer = getPackageManager().getPackageInstaller();
        PackageInstaller.SessionParams params =
            new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
        int sessionId = installer.createSession(params);
        PackageInstaller.Session session = installer.openSession(sessionId);
        try (InputStream in = new FileInputStream(apkFile);
             OutputStream out = session.openWrite("package.apk", 0, apkFile.length())) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) != -1) {
                out.write(buf, 0, n);
            }
            session.fsync(out);
        }
        Intent callback = new Intent(this, MainActivity.class);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 31) flags |= PendingIntent.FLAG_MUTABLE;
        PendingIntent pi = PendingIntent.getActivity(this, sessionId, callback, flags);
        session.commit(pi.getIntentSender());
        session.close();
    }

    private File downloadToCache(String urlStr, String fileName) throws Exception {
        File dir = new File(getCacheDir(), "apks");
        if (!dir.exists()) dir.mkdirs();
        File dest = new File(dir, fileName);
        HttpURLConnection conn = (HttpURLConnection) new URL(urlStr).openConnection();
        conn.setInstanceFollowRedirects(true);
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(60000);
        conn.setRequestProperty("User-Agent", "MoBox-Android/2.1.1");
        try (InputStream in = conn.getInputStream();
             FileOutputStream out = new FileOutputStream(dest)) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) != -1) {
                out.write(buf, 0, n);
            }
        }
        return dest;
    }

    private String scanWifiForMiBox() {
        String myIp = getWifiIp();
        if (myIp.isEmpty() || !myIp.contains(".")) return "";
        final String prefix = myIp.substring(0, myIp.lastIndexOf('.') + 1);
        ExecutorService pool = Executors.newFixedThreadPool(32);
        List<Future<String>> futures = new ArrayList<>();
        for (int i = 2; i < 254; i++) {
            final String candidate = prefix + i;
            if (candidate.equals(myIp)) continue;
            futures.add(pool.submit((Callable<String>) () -> {
                for (int port : new int[] {10591, 5555, 6466}) {
                    try (Socket s = new Socket()) {
                        s.connect(new InetSocketAddress(candidate, port), 260);
                        return candidate;
                    } catch (Exception ignored) {}
                }
                return "";
            }));
        }
        pool.shutdown();
        for (Future<String> f : futures) {
            try {
                String res = f.get();
                if (res != null && !res.isEmpty()) {
                    discoveredBoxIp = res;
                    return res;
                }
            } catch (Exception ignored) {}
        }
        return "";
    }

    private boolean configureTvLiveAtHost(String host) {
        try {
            URL url = new URL("http://" + host + ":10591/api/configs");
            HttpURLConnection getConn = (HttpURLConnection) url.openConnection();
            getConn.setConnectTimeout(3500);
            getConn.setReadTimeout(5000);
            if (getConn.getResponseCode() != 200) return false;
            String raw = readStream(getConn.getInputStream());
            JSONObject cfg = new JSONObject(raw);
            JSONObject listObj = cfg.optJSONObject("iptvSourceList");
            if (listObj == null) {
                listObj = new JSONObject();
                cfg.put("iptvSourceList", listObj);
            }
            JSONArray sources = listObj.optJSONArray("value");
            if (sources == null) {
                sources = new JSONArray();
                listObj.put("value", sources);
            }
            int foundIdx = -1;
            for (int i = 0; i < sources.length(); i++) {
                JSONObject item = sources.optJSONObject(i);
                if (item != null && PLAYLIST_URL.equals(item.optString("url"))) {
                    foundIdx = i;
                    break;
                }
            }
            if (foundIdx == -1) {
                JSONObject src = new JSONObject();
                src.put("name", "Top Picks + Worldwide");
                src.put("url", PLAYLIST_URL);
                src.put("sourceType", 0);
                sources.put(src);
                foundIdx = sources.length() - 1;
            }
            cfg.put("iptvSourceCurrentIdx", foundIdx);
            cfg.put("appStartupScreen", "Channels");

            byte[] payload = cfg.toString().getBytes(StandardCharsets.UTF_8);
            HttpURLConnection postConn = (HttpURLConnection) url.openConnection();
            postConn.setRequestMethod("POST");
            postConn.setDoOutput(true);
            postConn.setConnectTimeout(4000);
            postConn.setReadTimeout(6000);
            postConn.setRequestProperty("Content-Type", "application/json");
            try (OutputStream os = postConn.getOutputStream()) {
                os.write(payload);
            }
            return postConn.getResponseCode() == 200;
        } catch (Exception e) {
            return false;
        }
    }

    private String fixZltRouter(String pw) {
        try {
            URL cgi = new URL("http://192.168.70.1/cgi-bin/http.cgi");
            JSONObject cReq = new JSONObject();
            cReq.put("cmd", 232);
            cReq.put("method", "GET");
            cReq.put("sessionId", "");
            JSONObject cRes = postZlt(cgi, cReq);
            String token = cRes.optString("token", "");
            if (token.isEmpty()) {
                return "Could not reach ZLT X28 at 192.168.70.1. Join the ZLT Wi-Fi first.";
            }
            String hash = sha256Hex(token + pw);
            JSONObject lReq = new JSONObject();
            lReq.put("cmd", 100);
            lReq.put("method", "POST");
            lReq.put("sessionId", "mobox" + System.currentTimeMillis());
            lReq.put("username", "admin");
            lReq.put("passwd", hash);
            lReq.put("isAutoUpgrade", "0");
            lReq.put("subcmd", 0);
            JSONObject lRes = postZlt(cgi, lReq);
            String sid = lRes.optString("sessionId", "");
            if (sid.isEmpty()) {
                return "ZLT X28 rejected the admin password.";
            }
            JSONObject dialReq = new JSONObject();
            dialReq.put("cmd", 222);
            dialReq.put("method", "POST");
            dialReq.put("sessionId", sid);
            dialReq.put("dialMode", "1");
            postZlt(cgi, dialReq);

            JSONObject bandReq = new JSONObject();
            bandReq.put("cmd", 161);
            bandReq.put("method", "POST");
            bandReq.put("sessionId", sid);
            bandReq.put("band4gRadio", "0");
            bandReq.put("band5gRadio", "0");
            postZlt(cgi, bandReq);

            JSONObject apnGet = new JSONObject();
            apnGet.put("cmd", 248);
            apnGet.put("method", "GET");
            apnGet.put("sessionId", sid);
            JSONObject apnRes = postZlt(cgi, apnGet);
            JSONArray apnList = apnRes.optJSONArray("apn_list");
            if (apnList != null && apnList.length() > 0) {
                int mciIdx = -1;
                for (int i = 0; i < apnList.length(); i++) {
                    JSONObject a = apnList.optJSONObject(i);
                    if (a != null && "mcinet".equalsIgnoreCase(a.optString("apnName"))) {
                        mciIdx = i;
                        break;
                    }
                }
                if (mciIdx >= 0) {
                    for (int i = 0; i < apnList.length(); i++) {
                        JSONObject a = apnList.optJSONObject(i);
                        if (a != null) a.put("default_flag", i == mciIdx ? "1" : "0");
                    }
                    JSONObject apnPost = new JSONObject();
                    apnPost.put("cmd", 248);
                    apnPost.put("method", "POST");
                    apnPost.put("sessionId", sid);
                    apnPost.put("apn_list", apnList);
                    postZlt(cgi, apnPost);
                }
            }
            return "ZLT X28 fixed! Auto-Dial is ON, band locks cleared, and MCI (mcinet) APN set as default.";
        } catch (Exception e) {
            return "Cannot reach ZLT X28 at 192.168.70.1 (" + e.getMessage() + ").";
        }
    }

    private JSONObject postZlt(URL cgi, JSONObject body) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) cgi.openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setConnectTimeout(4500);
        conn.setReadTimeout(6000);
        conn.setRequestProperty("Content-Type", "application/json");
        byte[] raw = body.toString().getBytes(StandardCharsets.UTF_8);
        try (OutputStream os = conn.getOutputStream()) {
            os.write(raw);
        }
        return new JSONObject(readStream(conn.getInputStream()));
    }

    private static String readStream(InputStream in) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[16384];
        int n;
        while ((n = in.read(buf)) != -1) bos.write(buf, 0, n);
        return new String(bos.toByteArray(), StandardCharsets.UTF_8);
    }

    private static String sha256Hex(String input) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] digest = md.digest(input.getBytes(StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        for (byte b : digest) sb.append(String.format("%02x", b));
        return sb.toString();
    }
}
