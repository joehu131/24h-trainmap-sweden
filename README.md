# All Trains in a Day: Sweden

An interactive 24-hour visualization of passenger train movements across Sweden. Built with vanilla HTML5 Canvas and JavaScript without external runtime dependencies.

## System Architecture

```
                      DATA INGESTION PIPELINE
                     
 ┌──────────────────────┐        ┌─────────────────────────┐
 │ Trafiklab GTFS       │        │ OpenStreetMap (OSM)     │
 │ Sweden 3 Archive     │        │ High-Precision Tracks   │
 └──────────┬───────────┘        └────────────┬────────────┘
            │                                 │
            ▼                                 ▼
 ┌──────────────────────┐        ┌─────────────────────────┐
 │ prepare_osm_data.py  │        │ build_top25_final.py    │
 │ - Clean train series │        │ - Top 25 city centers   │
 │ - Snap to OSM tracks │        │ - 550m buffer dissolve  │
 │ - Coordinate filters │        │ - 10,686 physical rails │
 └──────────┬───────────┘        └────────────┬────────────┘
            │                                 │
            ▼                                 ▼
   sweden-trains-*.json               sweden-geo.json
   (3,320 weekday trips)              (Tracks & urban masses)
            │                                 │
            └────────────────┬────────────────┘
                             │
                             ▼
                    prepare_deploy.py
                    (Gzip Compression: 28.1 MB -> 5.7 MB)
                             │
                             ▼
                    CLIENT APPLICATION
                     
                     index.html
             ┌─────────────────────────┐
             │ Animation Loop (60 FPS) │
             │ ├─ Curved trail paths   │
             │ ├─ Operator filtering   │
             │ ├─ Category filtering   │
             │ ├─ Smooth zoom & pan    │
             │ ├─ Interactive tracking │
             │ ├─ Urban opacity slider │
             │ └─ Viewport mini-clock  │
             └─────────────────────────┘
```

---

## Key Features

| Feature | Description |
| :--- | :--- |
| **High-Precision OSM Tracks** | All 10,686 physical railway track segments extracted from OpenStreetMap, with trains smoothly routed along realistic switch curves. |
| **Top 25 Cohesive Urban Masses** | 550-meter buffer-dissolved urban footprints for Sweden's 25 largest cities (+ Oslo and Copenhagen), naturally conforming to coastlines and islands. |
| **Carrier & Operator Filter** | Interactive modal dialog to filter traffic by specific train operators (SJ, MTRX, Vy, Pågatåg, Öresundståg, etc.). |
| **Category Toggle Buttons** | Quick one-click category toggles in the bottom legend (High-Speed, Intercity, Regional, Night). |
| **7-Day Timetable Switcher** | Full Monday to Sunday schedule switching with service day variations. |
| **Interactive Tracking Mode** | Hover to highlight route lines with origin and destination. Click any train dot to lock tracking mode. |
| **Smooth Pan & Zoom** | Multi-touch, mouse wheel, and button zoom (0.8x to 16.0x) with pan constraints. |
| **Dynamic Viewport Clock** | Large northern clock when zoomed out, automatically transitioning to a floating mini-clock card when panning away. |
| **Display Settings Controls** | Sliders for railway track opacity, train dot scale, trail length, and urban footprint opacity (10% to 100%). |
| **Light & Dark Modes** | High-contrast dark theme and warm cartographic light theme with WCAG (Web Content Accessibility Guidelines) AA compliance. |

---

## Train Categories

| Category | Color | Included Services |
| :--- | :--- | :--- |
| **High-Speed** | `#0066d6` (Light) / `#5aa9ff` (Dark) | SJ Snabbtåg (X2000, SJ 3000), VR Snabbtåg, MTRX, Arlanda Express |
| **Intercity** | `#d84500` (Light) / `#ff7a45` (Dark) | SJ InterCity, Öresundståg, Snälltåget, Tågab |
| **Regional** | `#028e5a` (Light) / `#35d69a` (Dark) | Mälartåg, Pågatåg, Västtågen, Krösatågen, TiB (Tåg i Bergslagen), Norrtåg, Värmlandstrafik, SL Pendeltåg |
| **Night Trains** | `#b87b00` (Light) / `#ffd93d` (Dark) | SJ Nattåg, Vy Nattåg, EuroNight |
| **Cross-Border** | Muted Grey | Foreign route extensions into Norway (Oslo, Narvik) and Denmark (Copenhagen) |

---

## Project Structure

```
AllTrainsInADay_SWE/
├── index.html                 # Complete single-page application (Canvas + UI)
├── .github/workflows/
│   └── deploy.yml             # GitHub Actions automated deployment workflow
├── data/
│   ├── sweden-geo.json        # Coastlines, lakes, Top 25 urban footprints, 10,686 tracks
│   ├── sweden-geo.json.gz     # Gzip deployment asset (316 KB)
│   ├── sweden-trains-mon.json # Monday schedule (3,320 trips)
│   ├── sweden-trains-mon.json.gz # Gzip Monday schedule (859 KB)
│   ├── sweden-trains-tue.json # Tuesday schedule (3,320 trips)
│   ├── sweden-trains-wed.json # Wednesday schedule (3,320 trips)
│   ├── sweden-trains-thu.json # Thursday schedule (3,326 trips)
│   ├── sweden-trains-fri.json # Friday schedule (3,328 trips)
│   ├── sweden-trains-sat.json # Saturday schedule (2,336 trips)
│   └── sweden-trains-sun.json # Sunday schedule (2,297 trips)
└── scripts/
    ├── prepare_osm_data.py    # Main GTFS parser and OSM railway track snap router
    ├── build_top25_final.py   # Top 25 cohesive urban mass builder (550m buffer dissolve)
    └── prepare_deploy.py      # Gzip compression pipeline for GitHub Pages
```

---

## Running Locally

Start a local HTTP (Hypertext Transfer Protocol) server:

```bash
python -m http.server 8000
```

Open `http://localhost:8000` in your web browser.

## Environment Setup & API Keys

If you want to fetch or refresh the raw GTFS (General Transit Feed Specification) feed from Trafiklab, create a `.env` file in the project root:

```bash
# .env
TRAFIKLAB_API_KEY="your_trafiklab_api_key_here"
```

To obtain an API key:
1. Register for a free account at [Trafiklab.se](https://www.trafiklab.se/).
2. Create an API project for **GTFS Sverige 3** (operator feed) and copy your project API key.

---

## Data Pipeline & Rebuilding

The dataset uses GTFS (General Transit Feed Specification) Sweden 3 from Trafiklab.se and OpenStreetMap (OSM) railway ways.

To rebuild the data pipeline:

1. **Extract OSM Track Curves & Build Timetables**:
   ```bash
   python scripts/prepare_osm_data.py
   ```

2. **Generate Top 25 Cohesive Urban Masses**:
   ```bash
   python scripts/build_top25_final.py
   ```

3. **Compress Deployment Assets**:
   ```bash
   python scripts/prepare_deploy.py
   ```

---

## Deployment Guide (GitHub Pages)

This project includes an automated GitHub Actions deployment workflow in `.github/workflows/deploy.yml`.

### Enabling GitHub Pages:
1. Push your repository to GitHub.
2. Go to your repository **Settings** on GitHub.
3. In the left sidebar, click **Pages** (under the "Code and automation" section).
4. Under **Build and deployment** $\rightarrow$ **Source**, select **GitHub Actions**.
5. When code is pushed to the `main` branch, the workflow will automatically deploy the site.
6. Your live site will be published at `https://<username>.github.io/<repository-name>/`.
