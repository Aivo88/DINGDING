# DING DING

Nyrkkeilyn kierrosajastin isoilla napeilla, kelloäänillä ja loppulaskennalla.

Made by Antti Kääriäinen.

## Mitä täällä on

| Tiedosto | Tarkoitus |
|---|---|
| `index.html` | Koko sovellus (selainversio / PWA) |
| `manifest.webmanifest`, `sw.js` | Asennus aloitusnäyttöön ja offline-tuki |
| `icon-192.png`, `icon-512.png` | Sovelluksen kuvake |
| `build_android.py` | Luo Android-projektin (äänet, ikoni, natiivikoodi) |
| `.github/workflows/android.yml` | Kääntää APK:n jokaisesta muutoksesta |

## APK

Jokainen muutos `main`-haaraan kääntää uuden APK:n. Valmis tiedosto löytyy
**Releases**-osiosta nimellä `DINGDING.apk`.

APK-versiossa:
- taustamusiikki hiljenee kelloäänten ajaksi ja palaa sitten
- näyttö pysyy päällä
- Takaisin-nappi sulkee asetukset tai lopettaa treenin
- toimii täysin ilman nettiä

Allekirjoitus: repon Secrets-kohdassa `KEYSTORE_B64` ja `KEYSTORE_PASS`.
Ilman niitä APK allekirjoitetaan väliaikaisella avaimella, jolloin päivitys
vaatii vanhan version poistamisen.

## Selainversio

Settings → Pages → Deploy from a branch → `main` / `(root)`.
Avaa osoite Chromella ja valitse **Lisää aloitusnäyttöön**.
