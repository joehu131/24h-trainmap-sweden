# AllTrainsInADay_SWE: Project Context & Rules

## Project Overview
Interactive 24-hour visualization of Swedish passenger train traffic using vanilla HTML5 Canvas and JavaScript without external UI frameworks or bundling dependencies.

## Key Files & Architecture
- `index.html`: Complete single-page client application (Canvas rendering loop, spatial projection, UI modals).
- `scripts/build_all.py`: Master data pipeline runner.
- `scripts/prepare_osm_data.py`: Extracts OSM (OpenStreetMap) track geometry and processes 7-day GTFS (General Transit Feed Specification) timetables.
- `scripts/build_top25_final.py`: Generates municipal urban footprints for Sweden's top 25 cities.
- `scripts/prepare_deploy.py`: Compresses JSON data into `.json.gz` for GitHub Pages hosting.
- `data/`: Processed JSON and GZ assets. Raw uncompressed files over 50 MB should not be tracked directly in Git if rebuildable.

## Standard Development Workflows
1. **Local Preview**: Always test Canvas changes using a local HTTP (Hypertext Transfer Protocol) server to avoid CORS (Cross-Origin Resource Sharing) blocks:
   `python -m http.server 8000`
2. **Data Pipeline Rebuild**: Run `python scripts/build_all.py` from repository root when modifying schedule logic or track geometry.
3. **Pre-Deployment Check**: Ensure all `.json.gz` files in `data/` are synchronized with their `.json` counterparts via `scripts/prepare_deploy.py`.

## Coding & Architectural Conventions
- Vanilla JavaScript and CSS only. Do not introduce npm, bundlers, or external CSS frameworks.
- Canvas performance is critical: static layers (land, tracks, stations) must be pre-rendered to an offscreen buffer canvas.
- Maintain operator color mappings and speed derivative calculations in `index.html`.
