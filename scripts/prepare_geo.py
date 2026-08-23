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

def build_clean_railway_network(trains_file):
    print(f"Building clean curved railway track network from {trains_file}...")
    with open(trains_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    raw_corridors = []
    for tr in data['trips']:
        pts = tr['pts']
        coords = [[p[0], p[1]] for p in pts]
        
        cleaned = [coords[0]]
        for pt in coords[1:]:
            prev = cleaned[-1]
            if math.hypot(pt[0] - prev[0], pt[1] - prev[1]) >= 0.004:
                cleaned.append(pt)
        if len(cleaned) >= 2:
            raw_corridors.append(cleaned)

    grid_edges = set()
    track_segments = []
    
    for line in raw_corridors:
        for i in range(len(line) - 1):
            p1 = (round(line[i][0], 3), round(line[i][1], 3))
            p2 = (round(line[i+1][0], 3), round(line[i+1][1], 3))
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

    # 3. Dense Urban Center Footprints
    urban_centers = [
        ("Stockholm", 59.330, 18.058, 5.5, 1.2, 20),
        ("Göteborg", 57.708, 11.973, 4.5, 1.3, -30),
        ("Malmö", 55.609, 13.000, 3.8, 1.1, 45),
        ("Uppsala", 59.858, 17.646, 3.2, 1.1, 0),
        ("Västerås", 59.607, 16.552, 2.8, 1.1, 15),
        ("Örebro", 59.278, 15.212, 2.8, 1.1, -10),
        ("Linköping", 58.416, 15.626, 2.8, 1.1, 30),
        ("Helsingborg", 56.046, 12.705, 2.4, 1.2, -45),
        ("Jönköping", 57.784, 14.163, 2.6, 1.2, -20),
        ("Norrköping", 58.596, 16.183, 2.6, 1.1, 40),
        ("Lund", 55.707, 13.187, 2.2, 1.0, 10),
        ("Umeå", 63.829, 20.266, 2.6, 1.2, -25),
        ("Gävle", 60.676, 17.151, 2.5, 1.1, 15),
        ("Borås", 57.720, 12.936, 2.4, 1.1, 0),
        ("Södertälje", 59.196, 17.628, 2.2, 1.2, -15),
        ("Eskilstuna", 59.371, 16.508, 2.2, 1.1, 20),
        ("Halmstad", 56.670, 12.865, 2.2, 1.2, -35),
        ("Växjö", 56.877, 14.807, 2.2, 1.0, 0),
        ("Karlstad", 59.378, 13.499, 2.4, 1.2, -10),
        ("Sundsvall", 62.387, 17.315, 2.4, 1.2, 35),
        ("Östersund", 63.172, 14.636, 2.2, 1.1, -20),
        ("Trollhättan", 58.284, 12.296, 2.0, 1.2, 10),
        ("Luleå", 65.584, 22.165, 2.2, 1.2, 40),
        ("Kiruna", 67.869, 20.222, 1.8, 1.0, 0),
        ("Falun", 60.603, 15.636, 1.8, 1.1, 25),
        ("Borlänge", 60.485, 15.432, 2.0, 1.1, -15),
        ("Skövde", 58.390, 13.855, 2.0, 1.0, 0),
        ("Karlskrona", 56.166, 15.586, 1.6, 1.2, -45),
        ("Kristianstad", 56.033, 14.159, 1.8, 1.1, 15),
        ("Kalmar", 56.662, 16.358, 1.7, 1.2, -30),
        ("Skellefteå", 64.750, 20.954, 2.0, 1.1, 0),
        ("Visby", 57.635, 18.298, 1.6, 1.0, 15),
        ("Piteå", 65.317, 21.480, 1.6, 1.1, 0),
        ("Boden", 65.825, 21.688, 1.7, 1.0, 0),
        ("Gällivare", 67.133, 20.660, 1.5, 1.0, 0),
        ("Ystad", 55.430, 13.826, 1.4, 1.1, -45),
        ("Trelleborg", 55.375, 13.158, 1.4, 1.1, 0),
        ("Landskrona", 55.867, 12.860, 1.5, 1.1, 0),
        ("Varberg", 57.111, 12.249, 1.5, 1.1, 0),
        ("Nässjö", 57.653, 14.697, 1.5, 1.0, 0),
        ("Herrljunga", 58.077, 13.024, 1.2, 1.0, 0),
        ("Katrineholm", 58.996, 16.208, 1.5, 1.0, 0),
        ("Alvesta", 56.899, 14.556, 1.3, 1.0, 0),
        ("Hässleholm", 56.158, 13.764, 1.5, 1.0, 0)
    ]

    city_limits = []
    for c_name, lat, lon, rad, asp, ang in urban_centers:
        poly = create_urban_footprint(lon, lat, rad, num_points=14, aspect=asp, angle_deg=ang)
        city_limits.append(poly)

    # 4. Clean Curved Railway Tracks
    tracks = build_clean_railway_network(wed_trains)

    geo_out = {
        "outline": coastlines,
        "states": coastlines,
        "lakes": lakes,
        "city_limits": city_limits,
        "tracks": tracks
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(geo_out, f, separators=(',', ':'))

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Saved sweden-geo.json ({size_kb:.1f} KB) with {len(coastlines)} islands & coastline polygons, {len(lakes)} Swedish lakes, and {len(tracks)} clean curved railway tracks.")

if __name__ == '__main__':
    prepare_sweden_geo()
