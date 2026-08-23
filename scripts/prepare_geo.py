import json
import urllib.request
import os
import math
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

def create_urban_footprint(lon, lat, radius_km, num_points=14, aspect=1.0, angle_deg=0):
    lat_deg_per_km = 1.0 / 111.3
    lon_deg_per_km = 1.0 / (111.3 * math.cos(math.radians(lat)))
    
    rad_lat = radius_km * lat_deg_per_km
    rad_lon = radius_km * lon_deg_per_km * aspect
    
    ring = []
    seed = int((lon + lat) * 10000) % 100
    
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    for i in range(num_points):
        theta = (2 * math.pi * i) / num_points
        wobble = 0.88 + 0.20 * math.sin(theta * 3 + seed) + 0.08 * math.cos(theta * 5)
        dx = math.cos(theta) * rad_lon * wobble
        dy = math.sin(theta) * rad_lat * wobble
        
        rot_dx = dx * cos_a - dy * sin_a
        rot_dy = dx * sin_a + dy * cos_a
        
        ring.append([round(lon + rot_dx, 4), round(lat + rot_dy, 4)])
        
    ring.append(ring[0])
    return ring

def build_clean_railway_network(data_dir):
    print("Building clean curved railway track network from all active 7-day train services...")
    import glob

    raw_corridors = []
    week_files = sorted(glob.glob(os.path.join(data_dir, 'sweden-trains-*.json')))
    print(f"Aggregating active train paths from {len(week_files)} daily timetable files...")

    total_trips = 0
    for fpath in week_files:
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

    # Spatially clean and bundle parallel tracks tightly along true corridors
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

    # Stitch segments into continuous polylines
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
    wed_trains = os.path.join(data_dir, 'sweden-trains-wed.json')

    # 1. Fetch Natural Earth 10m Detailed Sweden Coastlines and Islands (includes Gotland, Öland, Blekinge Archipelago, Trossö)
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

    # 2. Fetch Natural Earth 10m Lakes strictly inside Sweden territory (filter out Finland/Norway lakes)
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
            
            rings = []
            if geom_type == 'Polygon':
                rings = coords
            elif geom_type == 'MultiPolygon':
                for poly in coords:
                    for ring in poly:
                        rings.append(ring)

            for ring in rings:
                if len(ring) < 3:
                    continue
                # Calculate lake centroid to check containment inside Sweden land polygon
                avg_lon = sum(p[0] for p in ring) / len(ring)
                avg_lat = sum(p[1] for p in ring) / len(ring)
                
                # Strict check: lake centroid must lie inside Sweden land boundary
                if any(point_in_poly(avg_lon, avg_lat, r) for r in raw_swe_rings):
                    simplified = [[round(p[0], 3), round(p[1], 3)] for p in ring]
                    lakes.append(simplified)

        print(f"Loaded {len(lakes)} Swedish lake polygons strictly within Swedish borders.")
    except Exception as e:
        print(f"Note: Could not load external lakes dataset: {e}")

    # 3. Real Satellite-Derived Urban Footprints (Core + Semi-Urban Metropolitan Fringe)
    urban_raw_path = os.path.join(data_dir, 'osm', 'sweden-urban-raw.json')
    core_urban = []
    semi_urban = []
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
                core_urban.extend(extract_rings(coords, 2))
            elif gtype == 'MultiPolygon':
                core_urban.extend(extract_rings(coords, 3))

        for ring in core_urban:
            cx = sum(p[0] for p in ring) / len(ring)
            cy = sum(p[1] for p in ring) / len(ring)
            expanded = []
            for p in ring:
                dx = (p[0] - cx) * 0.35
                dy = (p[1] - cy) * 0.35
                expanded.append([round(p[0] + dx, 3), round(p[1] + dy, 3)])
            semi_urban.append(expanded)
        print(f"Loaded {len(core_urban)} real satellite urban footprints + {len(semi_urban)} semi-urban buffers.")

    # 4. Clean Curved Railway Tracks (exclusively from active weekly services)
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
    print(f"Saved sweden-geo.json ({size_kb:.1f} KB) with {len(coastlines)} islands & coastline polygons, {len(lakes)} Swedish lakes, {len(core_urban)} urban footprints, and {len(tracks)} clean curved railway tracks.")

if __name__ == '__main__':
    prepare_sweden_geo()
