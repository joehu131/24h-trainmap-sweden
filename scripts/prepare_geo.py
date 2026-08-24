import json
import urllib.request
import os
import math
import random
from collections import defaultdict

def point_in_poly(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

# Major named cities from index.html that get urban zones
NAMED_CITIES_URBAN = [
    # Tier 1 (Metropolitan Centers)
    ("Stockholm", 59.329, 18.069, 8.0),
    ("Göteborg", 57.709, 11.975, 7.0),
    ("Malmö", 55.605, 13.004, 6.0),
    ("Uppsala", 59.858, 17.639, 5.0),
    ("Västerås", 59.610, 16.545, 4.5),
    ("Örebro", 59.274, 15.207, 4.5),
    ("Linköping", 58.411, 15.622, 4.5),
    ("Helsingborg", 56.046, 12.695, 4.5),
    ("Jönköping", 57.783, 14.162, 4.5),
    ("Norrköping", 58.588, 16.188, 4.5),
    ("Lund", 55.705, 13.191, 4.0),
    ("Karlstad", 59.379, 13.504, 4.0),
    ("Sundsvall", 62.391, 17.307, 4.5),
    ("Östersund", 63.179, 14.636, 4.0),
    ("Gävle", 60.675, 17.141, 4.0),
    ("Umeå", 63.829, 20.266, 4.5),
    ("Luleå", 65.584, 22.165, 4.5),
    ("Kiruna", 67.869, 20.222, 3.5),
    ("Visby", 57.635, 18.298, 3.5),
    ("Oslo", 59.914, 10.752, 7.5),
    ("København", 55.676, 12.568, 7.0),

    # Tier 2 (Regional Hubs & Key Junctions)
    ("Borås", 57.720, 12.936, 3.8),
    ("Halmstad", 56.670, 12.865, 3.8),
    ("Eskilstuna", 59.371, 16.508, 3.8),
    ("Södertälje", 59.196, 17.628, 3.8),
    ("Skövde", 58.390, 13.855, 3.2),
    ("Herrljunga", 58.077, 13.024, 2.0),
    ("Katrineholm", 58.996, 16.208, 2.5),
    ("Nässjö", 57.653, 14.697, 2.5),
    ("Alvesta", 56.899, 14.556, 2.2),
    ("Hässleholm", 56.158, 13.764, 2.8),
    ("Kristianstad", 56.033, 14.159, 3.2),
    ("Karlskrona", 56.166, 15.586, 3.2),
    ("Kalmar", 56.662, 16.358, 3.2),
    ("Växjö", 56.877, 14.807, 3.5),
    ("Trollhättan", 58.284, 12.296, 3.2),
    ("Uddevalla", 58.353, 11.937, 3.0),
    ("Varberg", 57.111, 12.249, 3.0),
    ("Kungsbacka", 57.487, 12.079, 3.0),
    ("Falkenberg", 56.913, 12.511, 2.8),
    ("Ystad", 55.430, 13.826, 2.8),
    ("Trelleborg", 55.375, 13.158, 2.8),
    ("Landskrona", 55.867, 12.860, 3.0),
    ("Ängelholm", 56.248, 12.860, 2.8),
    ("Mjölby", 58.324, 15.127, 2.5),
    ("Motala", 58.537, 15.036, 2.8),
    ("Falun", 60.603, 15.636, 3.2),
    ("Borlänge", 60.485, 15.432, 3.2),
    ("Mora", 61.004, 14.537, 2.5),
    ("Hudiksvall", 61.725, 17.108, 2.5),
    ("Söderhamn", 61.304, 17.060, 2.5),
    ("Härnösand", 62.632, 17.938, 2.8),
    ("Örnsköldsvik", 63.291, 18.718, 3.0),
    ("Skellefteå", 64.750, 20.954, 3.2),
    ("Piteå", 65.317, 21.480, 3.0),
    ("Boden", 65.825, 21.688, 3.0),
    ("Gällivare", 67.133, 20.660, 2.5),
    ("Åre", 63.399, 13.076, 2.2),
    ("Hallsberg", 59.066, 15.111, 2.5),
    ("Kristinehamn", 59.309, 14.108, 2.5),
    ("Arvika", 59.654, 12.592, 2.5),
    ("Ludvika", 60.149, 15.187, 2.5),
    ("Sala", 59.923, 16.604, 2.5),
    ("Enköping", 59.641, 17.082, 2.8),
    ("Märsta", 59.620, 17.861, 2.8),
    ("Sandviken", 60.620, 16.776, 2.8),
    ("Bollnäs", 61.348, 16.393, 2.5),
    ("Nyköping", 58.756, 17.004, 3.0),
    ("Alingsås", 57.929, 12.533, 2.8),
    ("Lidköping", 58.503, 13.161, 2.8),
    ("Falköping", 58.172, 13.557, 2.5),
    ("Karlshamn", 56.173, 14.862, 2.5),
    ("Älmhult", 56.551, 14.138, 2.2),
    ("Eslöv", 55.838, 13.303, 2.5)
]

def make_city_polygon(lon, lat, radius_km, num_pts=24, seed=42):
    rng = random.Random(seed + int(lat*100) + int(lon*100))
    lat_km = 111.0
    lon_km = 111.0 * math.cos(math.radians(lat))
    pts = []
    phase1 = rng.uniform(0, math.pi*2)
    phase2 = rng.uniform(0, math.pi*2)
    for i in range(num_pts):
        angle = (i / float(num_pts)) * math.pi * 2
        r_var = 1.0 + 0.22 * math.sin(2 * angle + phase1) + 0.12 * math.cos(3 * angle + phase2)
        r = radius_km * r_var
        dx_km = r * math.cos(angle)
        dy_km = r * math.sin(angle)
        p_lon = round(lon + dx_km / lon_km, 3)
        p_lat = round(lat + dy_km / lat_km, 3)
        pts.append([p_lon, p_lat])
    pts.append(pts[0])
    return pts

def build_named_cities_urban_layers(data_dir):
    urban_raw_path = os.path.join(data_dir, 'osm', 'sweden-urban-raw.json')
    raw_satellite_polys = []
    if os.path.exists(urban_raw_path):
        with open(urban_raw_path, 'r', encoding='utf-8') as f:
            urban_feats = json.load(f)
        for feat in urban_feats:
            geom = feat.get('geometry', {})
            gtype = geom.get('type')
            coords = geom.get('coordinates', [])
            def extract_rings(c_list, depth):
                rings = []
                if depth == 1:
                    ring = [[round(pt[0], 3), round(pt[1], 3)] for pt in c_list]
                    if len(ring) >= 4: rings.append(ring)
                else:
                    for sub in c_list: rings.extend(extract_rings(sub, depth - 1))
                return rings

            if gtype == 'Polygon':
                raw_satellite_polys.extend(extract_rings(coords, 2))
            elif gtype == 'MultiPolygon':
                raw_satellite_polys.extend(extract_rings(coords, 3))

    core_urban = []
    semi_urban = []

    for name, lat, lon, rad_km in NAMED_CITIES_URBAN:
        matched_satellite = None
        for poly in raw_satellite_polys:
            min_x = min(p[0] for p in poly)
            max_x = max(p[0] for p in poly)
            min_y = min(p[1] for p in poly)
            max_y = max(p[1] for p in poly)
            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            d = math.hypot(cx - lon, cy - lat)
            if d < 0.12 or (min_x - 0.03 <= lon <= max_x + 0.03 and min_y - 0.03 <= lat <= max_y + 0.03):
                matched_satellite = poly
                break

        if matched_satellite:
            core_urban.append(matched_satellite)
            cx = sum(p[0] for p in matched_satellite) / len(matched_satellite)
            cy = sum(p[1] for p in matched_satellite) / len(matched_satellite)
            semi_ring = []
            for p in matched_satellite:
                dx = (p[0] - cx) * 0.38
                dy = (p[1] - cy) * 0.38
                semi_ring.append([round(p[0] + dx, 3), round(p[1] + dy, 3)])
            semi_urban.append(semi_ring)
        else:
            core_urban.append(make_city_polygon(lon, lat, rad_km, num_pts=20))
            semi_urban.append(make_city_polygon(lon, lat, rad_km * 1.8, num_pts=24))

    print(f"Generated consistent urban footprints for {len(core_urban)} named cities (zero orphan unlabelled blobs).")
    return core_urban, semi_urban

def build_clean_railway_network(data_dir):
    print("Building clean curved railway track network from all active 7-day train services...")
    import glob

    raw_corridors = []
    week_files = sorted(glob.glob(os.path.join(data_dir, 'sweden-trains-*.json')))
    print(f"Aggregating active train paths from {len(week_files)} daily timetable files...")

    total_trips = 0
    for fpath in week_files:
        if '-osm' in fpath or '-compact' in fpath:
            continue
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        trips = data.get('trips', [])
        total_trips += len(trips)
        for tr in trips:
            pts = tr.get('pts', [])
            if len(pts) >= 2:
                coords = [(p[0], p[1]) for p in pts]
                raw_corridors.append(coords)

    print(f"Collected {len(raw_corridors)} active train paths from {total_trips} weekly services.")

    grid_edges = set()
    track_segments = []
    
    for line in raw_corridors:
        cleaned = [line[0]]
        for pt in line[1:]:
            prev = cleaned[-1]
            if math.hypot(pt[0] - prev[0], pt[1] - prev[1]) >= 0.003:
                cleaned.append(pt)
        if len(cleaned) < 2:
            continue

        for i in range(len(cleaned) - 1):
            p1 = (round(cleaned[i][0], 3), round(cleaned[i][1], 3))
            p2 = (round(cleaned[i+1][0], 3), round(cleaned[i+1][1], 3))
            if p1 != p2:
                if 54.5 <= p1[1] <= 70.0 and 54.5 <= p2[1] <= 70.0 and 9.0 <= p1[0] <= 26.0 and 9.0 <= p2[0] <= 26.0:
                    edge = tuple(sorted([p1, p2]))
                    if edge not in grid_edges:
                        grid_edges.add(edge)
                        track_segments.append([list(p1), list(p2)])

    adj = defaultdict(list)
    for seg in track_segments:
        p1 = (seg[0][0], seg[0][1])
        p2 = (seg[1][0], seg[1][1])
        adj[p1].append(p2)
        adj[p2].append(p1)

    visited_edges = set()
    continuous_tracks = []

    for seg in track_segments:
        p1 = (seg[0][0], seg[0][1])
        p2 = (seg[1][0], seg[1][1])
        edge = tuple(sorted([p1, p2]))
        if edge in visited_edges:
            continue

        line = [list(p1), list(p2)]
        visited_edges.add(edge)

        curr = p2
        prev = p1
        while len(adj[curr]) == 2:
            nxt = adj[curr][0] if adj[curr][0] != prev else adj[curr][1]
            next_edge = tuple(sorted([curr, nxt]))
            if next_edge in visited_edges:
                break
            visited_edges.add(next_edge)
            line.append(list(nxt))
            prev = curr
            curr = nxt

        curr = p1
        prev = p2
        while len(adj[curr]) == 2:
            nxt = adj[curr][0] if adj[curr][0] != prev else adj[curr][1]
            next_edge = tuple(sorted([curr, nxt]))
            if next_edge in visited_edges:
                break
            visited_edges.add(next_edge)
            line.insert(0, list(nxt))
            prev = curr
            curr = nxt

        continuous_tracks.append(line)

    print(f"Stitched railway network into {len(continuous_tracks)} continuous clean curved track polylines.")
    return continuous_tracks

def prepare_sweden_geo():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, 'sweden-geo.json')

    # 1. Natural Earth 10m Sweden Coastlines
    ne_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson"
    print(f"Fetching Natural Earth 10m high-resolution Sweden boundaries from {ne_url}...")
    req = urllib.request.Request(ne_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as resp:
        ne_data = json.loads(resp.read().decode('utf-8'))

    coastlines = []
    raw_swe_rings = []
    for f in ne_data.get('features', []):
        if f['properties'].get('ADM0_A3') == 'SWE' or f['properties'].get('NAME') == 'Sweden':
            geom = f.get('geometry', {})
            geom_type = geom.get('type')
            coords = geom.get('coordinates', [])
            if geom_type == 'Polygon':
                for ring in coords:
                    raw_swe_rings.append(ring)
                    simplified = [[round(pt[0], 3), round(pt[1], 3)] for pt in ring]
                    if len(simplified) >= 3:
                        coastlines.append(simplified)
            elif geom_type == 'MultiPolygon':
                for poly in coords:
                    for ring in poly:
                        raw_swe_rings.append(ring)
                        simplified = [[round(pt[0], 3), round(pt[1], 3)] for pt in ring]
                        if len(simplified) >= 3:
                            coastlines.append(simplified)
            break

    print(f"Loaded {len(coastlines)} detailed Sweden coastline & island polygons.")

    # 2. Natural Earth 10m Lakes
    lakes_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_lakes.geojson"
    print(f"Fetching Swedish lakes from {lakes_url}...")
    lakes = []
    try:
        req = urllib.request.Request(lakes_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=25) as resp:
            lakes_data = json.loads(resp.read().decode('utf-8'))
        
        for f in lakes_data.get('features', []):
            geom = f.get('geometry', {})
            geom_type = geom.get('type')
            coords = geom.get('coordinates', [])
            rings = coords if geom_type == 'Polygon' else [r for poly in coords for r in poly]

            for ring in rings:
                if len(ring) < 3: continue
                avg_lon = sum(p[0] for p in ring) / len(ring)
                avg_lat = sum(p[1] for p in ring) / len(ring)
                if any(point_in_poly(avg_lon, avg_lat, r) for r in raw_swe_rings):
                    simplified = [[round(p[0], 3), round(p[1], 3)] for p in ring]
                    lakes.append(simplified)

        print(f"Loaded {len(lakes)} Swedish lake polygons strictly within Swedish borders.")
    except Exception as e:
        print(f"Note: Could not load external lakes dataset: {e}")

    # 3. Consistent Named Cities Urban Footprints
    core_urban, semi_urban = build_named_cities_urban_layers(data_dir)

    # 4. Clean Railway Tracks
    tracks = build_clean_railway_network(data_dir)

    geo_out = {
        "outline": coastlines,
        "states": coastlines,
        "lakes": lakes,
        "city_limits": core_urban,
        "core_urban": core_urban,
        "semi_urban": semi_urban,
        "tracks": tracks
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(geo_out, f, separators=(',', ':'))

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Saved sweden-geo.json ({size_kb:.1f} KB) with {len(core_urban)} consistent urban footprints for named cities.")

if __name__ == '__main__':
    prepare_sweden_geo()
