# All Trains in a Day: Sweden

An interactive 24-hour visualization of passenger train movements across Sweden. Built with vanilla HTML5 Canvas and JavaScript without external runtime dependencies.

## System Architecture

```
                      DATA INGESTION PIPELINE
                     
 ┌──────────────────────┐        ┌─────────────────────────┐
 │ Trafiklab GTFS       │        │ Natural Earth 10m       │
 │ Sweden 3 Archive     │        │ Boundaries & Lakes      │
 └──────────┬───────────┘        └────────────┬────────────┘
            │                                 │
            ▼                                 ▼
 ┌──────────────────────┐        ┌─────────────────────────┐
 │ scripts/prepare_data │        │ scripts/prepare_geo.py  │
 │ - Filter rail routes │        │ - Coastlines (41 polys) │
 │ - Match shapes.txt   │        │ - 65 Swedish lakes      │
 │ - Corridor routing   │        │ - 44 Urban footprints   │
 └──────────┬───────────┘        │ - Continuous tracks     │
            │                    └────────────┬────────────┘
            ▼                                 ▼
   sweden-trains-*.json               sweden-geo.json
   (Mon - Sun schedules)              (Map vector layers)
            │                                 │
            └────────────────┬────────────────┘
                             │
                             ▼
                    CLIENT APPLICATION
                     
                     index.html
             ┌─────────────────────────┐
             │ Animation Loop (60 FPS) │
             │ ├─ Continuous head/tail │
             │ ├─ Canvas 2D map layers │
             │ ├─ Smooth zoom & pan    │
             │ ├─ Interactive tracking │
             │ └─ Viewport mini-clock  │
             └─────────────────────────┘
```

---

## Key Features

| Feature | Description |
| :--- | :--- |
| **Curved Track Geometry** | Train movements follow physical track shapes (*shapes.txt*) and railway corridors around lakes and coastlines. |
| **Lake & Island Cartography** | 65 major Swedish lakes (Vänern, Vättern, Mälaren, Hjälmaren, Siljan) and island coastlines rendered in high resolution. |
| **7-Day Timetable Switcher** | Full Monday to Sunday schedule switching with service day variations. |
| **Interactive Tracking Mode** | Hover to highlight full route lines with origin and destination. Click any train dot to lock tracking mode. |
| **Smooth Pan & Zoom** | Multi-touch, wheel, and button zoom (up to 6.0x) with pan boundary constraints. |
| **3-Tier Level of Detail** | Geographic labels scale dynamically: national hubs (Tier 1), regional junctions (Tier 2), and local station stops (Tier 3). |
| **Dynamic Viewport Clock** | Large Lapland clock when zoomed out, automatically transitioning to a floating mini-clock card when panning away. |
| **Custom Display Settings** | Adjust railway track opacity, train dot radius, trail length, and toggle urban footprints or city labels. |
| **Light and Dark Modes** | High-contrast dark theme and warm cartographic light theme with WCAG AA compliance. |

---

## Train Categories

| Category | Color | Included Services |
| :--- | :--- | :--- |
| **High-Speed** | `#0066d6` (Light) / `#5aa9ff` (Dark) | SJ Snabbtåg (X2000, SJ 3000), VR Snabbtåg, MTRX, Arlanda Express |
| **Intercity** | `#d84500` (Light) / `#ff7a45` (Dark) | SJ InterCity, Vy Tåg, Snälltåget, Øresundståg |
| **Regional** | `#028e5a` (Light) / `#35d69a` (Dark) | Mälartåg, Pågatågen, Västtågen, Krösatågen, TiB (Tåg i Bergslagen), Norrtåg |
| **Night Trains** | `#b87b00` (Light) / `#ffd93d` (Dark) | SJ Nattåg, Vy Nattåg, EuroNight |
| **Cross-Border** | Muted Grey | Foreign route extensions into Norway (Oslo, Narvik) and Denmark (Copenhagen) |

---

## Project Structure

```
AllTrainsInADay_SWE/
├── index.html                 # Complete single-page application (Canvas + UI)
├── data/
│   ├── sweden-geo.json        # Coastlines, islands, lakes, footprints, tracks (318 KB)
│   ├── sweden-trains-mon.json # Monday timetable with curved paths (2,958 trips)
│   ├── sweden-trains-tue.json # Tuesday timetable (2,963 trips)
│   ├── sweden-trains-wed.json # Wednesday timetable (2,960 trips)
│   ├── sweden-trains-thu.json # Thursday timetable (2,965 trips)
│   ├── sweden-trains-fri.json # Friday timetable (2,978 trips)
│   ├── sweden-trains-sat.json # Saturday timetable (1,960 trips)
│   └── sweden-trains-sun.json # Sunday timetable (1,967 trips)
└── scripts/
    ├── prepare_data.py        # GTFS parser and corridor curve generator
    └── prepare_geo.py         # Boundary, lake, footprint, and track generator
```

---

## Running Locally

Start a local HTTP (Hypertext Transfer Protocol) server:

```bash
cd AllTrainsInADay_SWE
python -m http.server 8000
```

Open `http://localhost:8000` in your web browser.

---

## Data Ingestion & Updates

The dataset uses GTFS (General Transit Feed Specification) Sweden 3 from Trafiklab.se.

To rebuild the data pipeline:

1. **Process Timetables**:
   ```bash
   python scripts/prepare_data.py
   ```
2. **Build Geographic Layers**:
   ```bash
   python scripts/prepare_geo.py
   ```
