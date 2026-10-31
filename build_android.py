#!/usr/bin/env python3
"""
DING DING – Android-projektin generaattori.

Ajetaan GitHub Actionsissa (.github/workflows/android.yml). Luo kansion android/,
jossa on pieni natiivi Android-sovellus:
  * näyttää index.html:n WebView'ssä (kaikki toimii ilman nettiä)
  * soittaa kelloäänet Androidin kautta ja pyytää "duck"-äänifokuksen,
    jolloin taustamusiikki (Spotify ym.) hiljenee hetkeksi ja palaa sitten
  * pitää näytön päällä niin kauan kuin sovellus on auki
  * Takaisin-nappi sulkee asetukset / lopettaa treenin

Ei vaadi mitään omia binääritiedostoja repoon: äänet syntetisoidaan tässä,
fontit haetaan Google Fontsista ja ikoni tehdään icon-512.png:stä.
"""
import math, os, re, shutil, struct, urllib.request, wave

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "android")
PKG = "fi.antti.dingding"
SKY = "#A1CFD3"
NAVY = "#1C2D42"
VERSION_NAME = "1.0"


def w(path, text):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text.lstrip("\n"))


# ---------------------------------------------------------------- äänet
RATE = 44100


def bell(buf, start, freq, gain, dur):
    parts = [(1, 1), (2.76, .45), (5.4, .25), (8.93, .12)]
    n0, n = int(start * RATE), int(dur * RATE)
    for i in range(n):
        if n0 + i >= len(buf):
            break
        t = i / RATE
        v = sum(a * math.sin(2 * math.pi * freq * m * t) * math.exp(-t * (2.2 + m * .9)) for m, a in parts)
        buf[n0 + i] += v * gain * min(1, i / 80)


def beep(buf, start, freq, gain, dur):
    n0, n = int(start * RATE), int(dur * RATE)
    for i in range(n):
        t = i / RATE
        buf[n0 + i] += gain * math.sin(2 * math.pi * freq * t) * min(1, i / 120) * min(1, (n - i) / 800)


def save_wav(name, buf):
    peak = max(abs(v) for v in buf) or 1
    k = .95 / peak
    path = os.path.join(OUT, "app/src/main/assets/sounds", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v * k)) * 32767)) for v in buf))


def make_sounds():
    b = [0.0] * int(RATE * 2.2); bell(b, 0, 880, 1, 2.2); save_wav("ding.wav", b)
    b = [0.0] * int(RATE * 3.0); bell(b, 0, 830, 1, 2.4); bell(b, .45, 830, 1, 2.5); save_wav("double.wav", b)
    b = [0.0] * int(RATE * .25); beep(b, 0, 1568, 1, .18); save_wav("tick.wav", b)


# ---------------------------------------------------------------- web-sisältö
def make_web():
    www = os.path.join(OUT, "app/src/main/assets/www")
    os.makedirs(www, exist_ok=True)
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    # Fontit mukaan pakettiin, jotta sovellus näyttää oikealta myös ilman nettiä
    m = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/[^"]+)">', html)
    if m:
        try:
            url = m.group(1).replace("&amp;", "&")
            ua = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124.0 Mobile Safari/537.36"}
            css = urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=30).read().decode()
            os.makedirs(os.path.join(www, "fonts"), exist_ok=True)
            for i, furl in enumerate(sorted(set(re.findall(r"url\((https://[^)]+)\)", css)))):
                fname = "f%d.woff2" % i
                data = urllib.request.urlopen(urllib.request.Request(furl, headers=ua), timeout=30).read()
                open(os.path.join(www, "fonts", fname), "wb").write(data)
                css = css.replace(furl, "fonts/" + fname)
            html = html.replace(m.group(0), "<style>\n" + css + "\n</style>")
            print("Fontit pakattu mukaan")
        except Exception as e:  # ilman fontteja käytetään varafontteja
            print("Fonttien haku epäonnistui:", e)
    # Service worker ja manifest eivät kuulu APK:hon
    html = re.sub(r'<link rel="manifest"[^>]*>\n?', "", html)
    open(os.path.join(www, "index.html"), "w", encoding="utf-8").write(html)
    for f in ("icon-192.png", "icon-512.png"):
        shutil.copy(os.path.join(ROOT, f), os.path.join(www, f))


# ---------------------------------------------------------------- ikoni
def make_icon():
    res = os.path.join(OUT, "app/src/main/res")
    os.makedirs(os.path.join(res, "drawable-nodpi"), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "icon-512.png"), os.path.join(res, "drawable-nodpi/ic_logo.png"))
    w("app/src/main/res/drawable/ic_fg.xml", """
<inset xmlns:android="http://schemas.android.com/apk/res/android"
    android:drawable="@drawable/ic_logo" android:inset="14%" />
""")
    w("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", """
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/sky" />
    <foreground android:drawable="@drawable/ic_fg" />
</adaptive-icon>
""")
    w("app/src/main/res/values/colors.xml", f"""
<resources>
    <color name="sky">{SKY}</color>
    <color name="navy">{NAVY}</color>
</resources>
""")


# ---------------------------------------------------------------- gradle + koodi
def make_project():
    run = os.environ.get("GITHUB_RUN_NUMBER", "1")
    w("settings.gradle", """
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositories { google(); mavenCentral() }
}
rootProject.name = "DINGDING"
include ':app'
""")
    w("build.gradle", """
plugins { id 'com.android.application' version '8.5.2' apply false }
""")
    w("gradle.properties", """
org.gradle.jvmargs=-Xmx2g
android.nonTransitiveRClass=true
""")
    w("app/build.gradle", f"""
plugins {{ id 'com.android.application' }}

def ksFile = System.getenv('KS_FILE')

android {{
    namespace '{PKG}'
    compileSdk 34

    defaultConfig {{
        applicationId '{PKG}'
        minSdk 26
        targetSdk 34
        versionCode {run}
        versionName '{VERSION_NAME}.{run}'
    }}

    if (ksFile) {{
        signingConfigs {{
            release {{
                storeFile file(ksFile)
                storePassword System.getenv('KS_PASS')
                keyAlias 'dingding'
                keyPassword System.getenv('KS_PASS')
            }}
        }}
    }}

    buildTypes {{
        release {{
            minifyEnabled false
            signingConfig ksFile ? signingConfigs.release : signingConfigs.debug
        }}
    }}

    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}

    androidResources {{ noCompress 'wav' }}
}}
""")
    w("app/src/main/AndroidManifest.xml", """
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:label="DING DING"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher"
        android:allowBackup="true"
        android:theme="@style/AppTheme">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:screenOrientation="portrait"
            android:configChanges="orientation|screenSize|keyboardHidden|uiMode">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
""")
    w("app/src/main/res/values/styles.xml", """
<resources>
    <style name="AppTheme" parent="@android:style/Theme.Material.NoActionBar">
        <item name="android:windowBackground">@color/navy</item>
        <item name="android:statusBarColor">@color/navy</item>
        <item name="android:navigationBarColor">@color/navy</item>
    </style>
</resources>
""")
    w(f"app/src/main/java/{PKG.replace('.', '/')}/MainActivity.java", f"""
package {PKG};

import android.app.Activity;
import android.content.res.AssetFileDescriptor;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.media.SoundPool;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.util.HashMap;
import java.util.Map;

public class MainActivity extends Activity {{
    private WebView web;
    private SoundPool pool;
    private AudioManager audio;
    private AudioFocusRequest focus;
    private final Map<String, Integer> ids = new HashMap<>();
    private final Map<String, Integer> lengths = new HashMap<>();
    private final Handler main = new Handler(Looper.getMainLooper());
    // Musiikki palaa normaaliksi, kun ääni on loppunut ja tämä viive kulunut
    private final Runnable releaseFocus = () -> {{ if (focus != null) audio.abandonAudioFocusRequest(focus); }};

    @Override
    protected void onCreate(Bundle state) {{
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        AudioAttributes attrs = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build();
        audio = (AudioManager) getSystemService(AUDIO_SERVICE);
        focus = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .setAudioAttributes(attrs)
                .build();
        pool = new SoundPool.Builder().setMaxStreams(4).setAudioAttributes(attrs).build();
        load("ding", 2200);
        load("double", 3000);
        load("tick", 250);

        web = new WebView(this);
        web.setBackgroundColor(0xFF1C2D42);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(true);
        web.setWebViewClient(new WebViewClient());
        web.addJavascriptInterface(new Bridge(), "DingNative");
        setContentView(web);
        if (state != null) web.restoreState(state);
        else web.loadUrl("file:///android_asset/www/index.html");
    }}

    private void load(String name, int ms) {{
        try (AssetFileDescriptor fd = getAssets().openFd("sounds/" + name + ".wav")) {{
            ids.put(name, pool.load(fd, 1));
            lengths.put(name, ms);
        }} catch (Exception e) {{
            e.printStackTrace();
        }}
    }}

    private class Bridge {{
        @JavascriptInterface
        public void play(String name) {{
            main.post(() -> {{
                Integer id = ids.get(name);
                if (id == null) return;
                audio.requestAudioFocus(focus);
                main.removeCallbacks(releaseFocus);
                pool.play(id, 1f, 1f, 1, 0, 1f);
                Integer len = lengths.get(name);
                main.postDelayed(releaseFocus, (len == null ? 1000 : len) + 1500);
            }});
        }}

        @JavascriptInterface
        public void stop() {{
            main.post(() -> {{
                pool.autoPause();
                main.removeCallbacks(releaseFocus);
                releaseFocus.run();
            }});
        }}
    }}

    @Override
    public void onBackPressed() {{
        web.evaluateJavascript("window.dingBack ? window.dingBack() : false", v -> {{
            if (!"true".equals(v)) super.onBackPressed();
        }});
    }}

    @Override
    protected void onSaveInstanceState(Bundle out) {{
        super.onSaveInstanceState(out);
        web.saveState(out);
    }}

    @Override
    protected void onDestroy() {{
        main.removeCallbacksAndMessages(null);
        releaseFocus.run();
        if (pool != null) pool.release();
        if (web != null) web.destroy();
        super.onDestroy();
    }}
}}
""")


if __name__ == "__main__":
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    make_project()
    make_icon()
    make_sounds()
    make_web()
    print("Android-projekti luotu:", OUT)
