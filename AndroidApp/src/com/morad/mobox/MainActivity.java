package com.morad.mobox;

import android.app.Activity;
import android.app.PendingIntent;
import android.app.UiModeManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageInstaller;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.net.Uri;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.StatFs;
import android.provider.Settings;
import android.view.KeyEvent;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
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

public class MainActivity extends Activity {
    private WebView webView;
    private volatile String progressLabel = "Ready";
    private volatile int progressStep = 0;
    private volatile int progressTotal = 7;
    private volatile boolean busy = false;
    private volatile String discoveredBoxIp = "";

    private static final String PLAYLIST_URL =
        "https://raw.githubusercontent.com/aghamorad/mibox-fixer/main/playlists/world.m3u";

    private static final String[][] CORE_APPS = new String[][] {
        // key, title, pkg, url32, url64
        {
            "hume",
            "Hume Launcher (Apple TV-style)",
            "com.petrobot.hume",
            "https://github.com/petrobot-admin/hume-launcher/releases/download/v7.8/HumeLauncher-7.8.apk",
            "https://github.com/petrobot-admin/hume-launcher/releases/download/v7.8/HumeLauncher-7.8.apk"
        },
        {
            "mytv",
            "TV Live (Worldwide & Iran IPTV)",
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
            "MATVT (Mouse & Scroll Helper)",
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

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        webView = new WebView(this);
        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setAllowFileAccess(true);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.setBackgroundColor(0xFF0D0F14);
        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient());
        webView.addJavascriptInterface(this, "MoBoxNative");

        setContentView(webView);
        webView.loadUrl("file:///android_asset/index.html");
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView != null && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

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
        conn.setRequestProperty("User-Agent", "MoBox-Android/2.1.0");
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

        @JavascriptInterface
        public String getStatusJson() {
            try {
                JSONObject root = new JSONObject();
                boolean isTv = isTvDevice();
                boolean arm64 = is64Bit();
                root.put("version", "2.1.0");
                root.put("is_tv", isTv);
                root.put("model", Build.MODEL);
                root.put("manufacturer", Build.MANUFACTURER);
                root.put("android_release", Build.VERSION.RELEASE);
                root.put("sdk", Build.VERSION.SDK_INT);
                root.put("build_id", Build.DISPLAY);
                root.put("arch_label", arm64 ? "64-bit (arm64-v8a)" : "32-bit (armeabi-v7a)");
                root.put("free_storage_mb", getFreeStorageMb());
                root.put("wifi_ip", getWifiIp());
                root.put("discovered_box_ip", discoveredBoxIp);
                root.put("busy", busy);
                root.put("step", progressStep);
                root.put("total", progressTotal);
                root.put("label", progressLabel);

                JSONArray apps = new JSONArray();
                for (String[] row : CORE_APPS) {
                    JSONObject a = new JSONObject();
                    a.put("key", row[0]);
                    a.put("title", row[1]);
                    a.put("package", row[2]);
                    a.put("url", arm64 ? row[4] : row[3]);
                    a.put("installed", isPackageInstalled(row[2]));
                    apps.put(a);
                }
                root.put("apps", apps);
                return root.toString();
            } catch (Exception e) {
                return "{}";
            }
        }

        @JavascriptInterface
        public void runOneClickSetup() {
            if (busy) return;
            busy = true;
            progressStep = 0;
            progressTotal = CORE_APPS.length + 1;
            progressLabel = "Checking your device processor and installed apps…";

            new Thread(() -> {
                try {
                    boolean arm64 = is64Bit();
                    int idx = 0;
                    for (String[] row : CORE_APPS) {
                        idx++;
                        progressStep = idx;
                        String title = row[1];
                        String pkg = row[2];
                        String url = arm64 ? row[4] : row[3];
                        if (isPackageInstalled(pkg)) {
                            progressLabel = "Keeping existing " + title;
                            Thread.sleep(250);
                            continue;
                        }
                        progressLabel = "Downloading " + title + "…";
                        File apk = downloadToCache(url, row[0] + ".apk");
                        progressLabel = "Prompting install for " + title + "…";
                        installApkSession(apk);
                        Thread.sleep(1500);
                    }
                    progressStep = progressTotal;
                    progressLabel = "Programming TV Live Worldwide + Iran channels…";
                    boolean tvOk = configureTvLiveAtHost("127.0.0.1");
                    if (!tvOk && !discoveredBoxIp.isEmpty()) {
                        tvOk = configureTvLiveAtHost(discoveredBoxIp);
                    }
                    progressLabel = tvOk
                        ? "All done! Apps queued and TV Live channels programmed."
                        : "Apps ready! Open TV Live once, then tap 'Program TV Live Channels'.";
                } catch (Exception e) {
                    progressLabel = "Setup note: " + e.getMessage();
                } finally {
                    busy = false;
                }
            }).start();
        }

        @JavascriptInterface
        public void installSingleApp(final String key) {
            if (busy) return;
            new Thread(() -> {
                busy = true;
                try {
                    boolean arm64 = is64Bit();
                    for (String[] row : CORE_APPS) {
                        if (row[0].equals(key)) {
                            progressLabel = "Downloading " + row[1] + "…";
                            File apk = downloadToCache(arm64 ? row[4] : row[3], key + ".apk");
                            progressLabel = "Opening installer for " + row[1] + "…";
                            installApkSession(apk);
                            break;
                        }
                    }
                } catch (Exception e) {
                    progressLabel = "Install failed: " + e.getMessage();
                } finally {
                    busy = false;
                }
            }).start();
        }

        @JavascriptInterface
        public String scanWifiForMiBox() {
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

        @JavascriptInterface
        public String programTvLiveOnWifi(String host) {
            String target = (host == null || host.trim().isEmpty())
                ? (discoveredBoxIp.isEmpty() ? "127.0.0.1" : discoveredBoxIp)
                : host.trim();
            boolean ok = configureTvLiveAtHost(target);
            return ok
                ? "TV Live at " + target + " programmed with Top Picks + Worldwide!"
                : "Could not reach TV Live at " + target + ":10591. Make sure TV Live is open on the TV.";
        }

        @JavascriptInterface
        public void openSystemScreen(String which) {
            try {
                Intent intent;
                switch (which) {
                    case "screensaver":
                        intent = new Intent(Settings.ACTION_DREAM_SETTINGS);
                        break;
                    case "accessibility":
                        intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
                        break;
                    case "home":
                        intent = new Intent(Settings.ACTION_HOME_SETTINGS);
                        break;
                    case "bluetooth":
                        intent = new Intent(Settings.ACTION_BLUETOOTH_SETTINGS);
                        break;
                    default:
                        intent = new Intent(Settings.ACTION_SETTINGS);
                        break;
                }
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            } catch (Exception ignored) {}
        }

        @JavascriptInterface
        public String fixZltRouter(String adminPassword) {
            String pw = (adminPassword == null || adminPassword.isEmpty()) ? "admin" : adminPassword;
            try {
                URL cgi = new URL("http://192.168.70.1/cgi-bin/http.cgi");
                // 1. Challenge token (cmd 232)
                JSONObject cReq = new JSONObject();
                cReq.put("cmd", 232);
                cReq.put("method", "GET");
                cReq.put("sessionId", "");
                JSONObject cRes = postZlt(cgi, cReq);
                String token = cRes.optString("token", "");
                if (token.isEmpty()) {
                    return "Could not get login token from 192.168.70.1. Join the ZLT X28 Wi-Fi first.";
                }
                // 2. Login (cmd 100)
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
                // 3. Enable Auto-Dial (cmd 222)
                JSONObject dialReq = new JSONObject();
                dialReq.put("cmd", 222);
                dialReq.put("method", "POST");
                dialReq.put("sessionId", sid);
                dialReq.put("dialMode", "1");
                postZlt(cgi, dialReq);

                // 4. Clear stuck band lock (cmd 161)
                JSONObject bandReq = new JSONObject();
                bandReq.put("cmd", 161);
                bandReq.put("method", "POST");
                bandReq.put("sessionId", sid);
                bandReq.put("band4gRadio", "0");
                bandReq.put("band5gRadio", "0");
                postZlt(cgi, bandReq);

                // 5. Fix broken empty Auto APN -> set default_flag onto MCI mcinet if present (cmd 248)
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
                return "ZLT X28 fixed: Auto-Dial enabled, stuck band locks cleared, and MCI APN verified.";
            } catch (Exception e) {
                return "Cannot reach ZLT X28 at 192.168.70.1 (" + e.getMessage() + "). Connect to the ZLT Wi-Fi first.";
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
}
