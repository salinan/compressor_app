# Compressor App — Technical Specification

## Doel

Een Windows desktop applicatie die 4 bestandscompressie-tools bundelt in één interface:
- **JPG** — comprimeer losse JPEG afbeeldingen (bijv. Calibre boekomslagen)
- **EPUB** — comprimeer afbeeldingen binnenin EPUB bestanden
- **PDF** — comprimeer PDF bestanden via Ghostscript
- **CBZ/CBR** — comprimeer afbeeldingen binnenin comic archieven

De app is bedoeld voor grote bibliotheken (300.000+ bestanden). Tools kunnen parallel draaien.
Geschreven in Python met CustomTkinter voor de UI.

---

## Mappenstructuur

```
compressor_app/
├── main.py                  # Entry point — start de app
├── config.json              # Opgeslagen gebruikersinstellingen (auto-aangemaakt)
├── requirements.txt         # Python dependencies
├── core/
│   ├── shared.py            # Gedeelde functies voor alle tools
│   ├── jpg_compressor.py    # JPG compressie logica
│   ├── epub_compressor.py   # EPUB compressie logica
│   ├── pdf_compressor.py    # PDF compressie logica (via Ghostscript)
│   └── cbz_compressor.py    # CBZ/CBR compressie logica
└── ui/
    ├── app.py               # Hoofdvenster met tab-navigatie
    ├── components.py        # Herbruikbare UI-widgets
    └── tabs/
        ├── jpg_tab.py
        ├── epub_tab.py
        ├── pdf_tab.py
        └── cbz_tab.py
```

---

## Architectuur

### Threading model
- Elke tab draait zijn eigen `threading.Thread`
- Stop-signaal via `threading.Event` — stopt na het huidige bestand (niet halverwege)
- UI-updates via CustomTkinter's `after()` methode (thread-safe)
- App afsluiten tijdens verwerking = direct stoppen (geen wachten)

### Config systeem
Instellingen worden opgeslagen in `config.json` in de app-map.
Bij eerste start wordt het bestand aangemaakt met standaardwaarden.

```json
{
  "jpg": {
    "path": "",
    "target_width": 180,
    "target_height": 270,
    "quality": 70
  },
  "epub": {
    "path": "",
    "target_height": 450,
    "quality": 65
  },
  "pdf": {
    "path": "",
    "gs_path": "C:\\Program Files (x86)\\gs\\gs10.04.0\\bin\\gswin32c.exe",
    "pdf_settings": "/ebook"
  },
  "cbz": {
    "path": "",
    "target_width": 1200,
    "quality": 70
  }
}
```

### Marker-bestand systeem
Elk verwerkt bestand krijgt een `.compressed` marker naast zich:
- `cover.jpg` → `cover.jpg.compressed`
- Marker bevat datum/tijd van verwerking als tekst
- Als marker bestaat → bestand overslaan
- `Force` modus negeert markers (per tool instelbaar)

---

## core/shared.py

Bevat gedeelde functies die alle 4 tools gebruiken:

```python
def should_process_file(file_path: Path) -> bool
    # Controleert of .compressed marker bestaat
    # Returns True als bestand verwerkt moet worden

def mark_as_processed(file_path: Path) -> None
    # Maakt .compressed marker aan met huidige datum/tijd

def setup_logging(tool_name: str) -> logging.Logger
    # Configureert logging naar console + logbestand
    # Logbestand: {tool_name}_{datum_tijd}.log

def format_bytes(bytes: int) -> str
    # Bijv: 1.234.567 → "1.18 MB"
```

---

## UI Componenten (ui/components.py)

### PathSelector
Widget met:
- Label
- Tekstinvoer voor pad
- "Bladeren" knop (opent mapkiezer)
- Opslaat pad automatisch naar config bij wijziging

### LogViewer
- Scrollend tekstgebied (donkere achtergrond, monospace font)
- Methode `append(text)` voor thread-safe toevoegen van regels
- Auto-scroll naar beneden
- "Wis log" knop

### ProgressBar
- CustomTkinter progress bar
- Label eronder: "1.247 / 55.000 bestanden"
- Methode `update(current, total)`

### StatsPanel
- Toont na afloop: Succesvol / Overgeslagen / Mislukt / Bespaard (MB)
- Wordt bijgewerkt tijdens verwerking

### StartStopButton
- Toont "Start" als tool niet draait
- Toont "Stop" (rood) als tool actief is
- Disabled tijdens opstarten

---

## UI Tabs

Elke tab heeft dezelfde basisopbouw:

```
┌─────────────────────────────────────────┐
│  Pad:  [________________________] [...]  │
│                                         │
│  Instellingen (kwaliteit, afmetingen)   │
│                                         │
│  [        Start verwerking        ]     │
│                                         │
│  Voortgang: ████████░░ 1.247 / 55.000  │
│                                         │
│  Succesvol: 892  Overgeslagen: 312      │
│  Mislukt: 43     Bespaard: 234.5 MB    │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 14:32:01 - Verwerken: cover.jpg │   │
│  │ 14:32:01 - Bespaard: 45.2%      │   │
│  │ 14:32:02 - Verwerken: ...       │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### jpg_tab.py — Instellingen
- Pad selectie
- Breedte (standaard: 180px)
- Hoogte (standaard: 270px)
- Kwaliteit slider (standaard: 70, range: 50-95)
- Force checkbox (herverwerk ook al verwerkte bestanden)

### epub_tab.py — Instellingen
- Pad selectie
- Doelhoogte (standaard: 450px)
- Kwaliteit slider (standaard: 65, range: 50-95)

### pdf_tab.py — Instellingen
- Pad selectie
- Ghostscript pad (tekstinvoer + bladeren knop)
- PDF kwaliteit dropdown: `/screen` / `/ebook` / `/printer` / `/prepress`
- Waarschuwing als GS-pad niet bestaat

### cbz_tab.py — Instellingen
- Pad selectie
- Doelbreedte (standaard: 1200px)
- Kwaliteit slider (standaard: 70, range: 50-95)
- Opmerking: CBR vereist `rar.exe` in PATH

---

## core/ — Compressie modules

De core-modules zijn refactors van de bestaande scripts, aangepast voor gebruik in de app:

### Aanpassingen t.o.v. originele scripts
1. **Geen hardcoded paden** — `main()` krijgt alle instellingen als parameters
2. **Stop-event parameter** — `main(path, ..., stop_event: threading.Event)`
   - Controleer `stop_event.is_set()` aan het begin van elke bestandsiteratie
3. **Progress callback** — `main(path, ..., progress_callback=None)`
   - Roep aan met `(current, total, filename)` bij elk bestand
4. **Log callback** — `main(path, ..., log_callback=None)`
   - Roep aan met `(message)` in plaats van direct `logging.info()`
5. **Return statistieken** — `main()` geeft dict terug:
   ```python
   {"total": 1000, "successful": 892, "skipped": 312, "failed": 43, "bytes_saved": 245800000}
   ```

---

## main.py

```python
import customtkinter as ctk
from ui.app import CompressorApp

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = CompressorApp()
    app.mainloop()
```

---

## ui/app.py — Hoofdvenster

- `CTk` venster, titel: "Calibre Compressor"
- Minimumgrootte: 900x700
- `CTkTabview` met 4 tabs: JPG, EPUB, PDF, CBZ/CBR
- Laadt config bij opstarten
- Slaat config op bij afsluiten
- Bij afsluiten: alle actieve threads stoppen via hun stop_events

---

## requirements.txt

```
customtkinter>=5.2.0
Pillow>=10.0.0
rarfile>=4.0
```

Ghostscript is een externe installatie (niet via pip).
PyInstaller wordt gebruikt voor distributie als `.exe`.

---

## Bouwinstructies voor Claude Code

1. Maak de volledige mappenstructuur aan
2. Begin met `core/shared.py` — alle tools hangen hiervan af
3. Refactor de 4 compressie-scripts naar `core/` met de aanpassingen beschreven hierboven
4. Bouw `ui/components.py` — herbruikbare widgets
5. Bouw de 4 tab-bestanden in `ui/tabs/`
6. Bouw `ui/app.py` — hoofdvenster met tab-navigatie en config beheer
7. Schrijf `main.py` als entry point
8. Maak `requirements.txt` aan
9. Test met een kleine testmap voordat je op de volledige bibliotheek draait

### Prioriteit bij twijfel
- Correctheid boven snelheid
- Veiligheid: nooit een origineel bestand verwijderen zonder succesvolle vervanging
- Logging: altijd duidelijk wat er gebeurt en waarom
