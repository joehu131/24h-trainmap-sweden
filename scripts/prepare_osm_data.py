import os
import json
import math
import heapq
import zipfile
import csv
from collections import defaultdict
from datetime import datetime

DATA_DIR = "data"
OSM_RAW_PATH = os.path.join(DATA_DIR, "osm", "sweden-raw-rail.json")
URBAN_RAW_PATH = os.path.join(DATA_DIR, "osm", "sweden-urban-raw.json")
ZIP_PATH = os.path.join(DATA_DIR, "sweden.zip")

print("=== Building Option B: OpenStreetMap (OSM) High-Precision Railway Dataset ===")

# 1. Load OSM raw railway geometries (including Kongsvingerbanan into Oslo)
with open(OSM_RAW_PATH, 'r', encoding='utf-8') as f:
    osm_elements = json.load(f)

print(f"Loaded {len(osm_elements)} OSM raw railway ways.")

# 2. Build spatial topological network graph from OSM
fine_graph = defaultdict(dict)
for elem in osm_elements:
    geom = elem.get('geometry', [])
    if len(geom) < 2:
        continue
    line = [(round(p['lon'], 4), round(p['lat'], 4)) for p in geom if 54.5 <= p['lat'] <= 70.0 and 9.0 <= p['lon'] <= 26.0]
    for i in range(len(line) - 1):
        u, v = line[i], line[i+1]
        if u != v:
            d = math.hypot(v[0] - u[0], v[1] - u[1])
            if v not in fine_graph[u] or d < fine_graph[u][v]:
                fine_graph[u][v] = d
            if u not in fine_graph[v] or d < fine_graph[v][u]:
                fine_graph[v][u] = d

# Connect close switches (< 60m)
nodes = list(fine_graph.keys())
bucket_size = 0.005
buckets = defaultdict(list)
for n in nodes:
    buckets[(int(n[0]/bucket_size), int(n[1]/bucket_size))].append(n)

added_switches = 0
for (bx, by), b_nodes in buckets.items():
    cands = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cands.extend(buckets.get((bx + dx, by + dy), []))
    for i in range(len(b_nodes)):
        n1 = b_nodes[i]
        for n2 in cands:
            if n1 < n2:
                d = math.hypot(n2[0] - n1[0], n2[1] - n1[1])
                if 0 < d <= 0.0008:
                    if n2 not in fine_graph[n1]:
                        fine_graph[n1][n2] = d
                        fine_graph[n2][n1] = d
                        added_switches += 1

print(f"Base fine graph: {len(nodes)} nodes. Added {added_switches} switch connections.")

# 3. Load active stations from GTFS and include as junction nodes
def find_nearest_fine_node(pt):
    bx = int(pt[0] / bucket_size)
    by = int(pt[1] / bucket_size)
    cands = []
    for dx in range(-8, 9):
        for dy in range(-8, 9):
            cands.extend(buckets.get((bx + dx, by + dy), []))
    if not cands:
        return None
    return min(cands, key=lambda n: math.hypot(n[0] - pt[0], n[1] - pt[1]))

active_stations = set()
with zipfile.ZipFile(ZIP_PATH, 'r') as z:
    with z.open('stops.txt') as f:
        for r in csv.DictReader(f.read().decode('utf-8-sig').splitlines()):
            try:
                lon = round(float(r['stop_lon']), 4)
                lat = round(float(r['stop_lat']), 4)
                snapped = find_nearest_fine_node((lon, lat))
                if snapped and math.hypot(snapped[0] - lon, snapped[1] - lat) < 0.05:
                    active_stations.add(snapped)
            except ValueError:
                pass

print(f"Snapped {len(active_stations)} active stations to fine rail graph.")

# 4. Condense degree-2 interior nodes into edge polylines for fast A*
junction_nodes = set(n for n, adj in fine_graph.items() if len(adj) != 2)
junction_nodes.update(active_stations)

junction_graph = defaultdict(dict)
visited_edges = set()

for j in junction_nodes:
    for nxt in fine_graph[j]:
        edge = tuple(sorted([j, nxt]))
        if edge in visited_edges:
            continue
        visited_edges.add(edge)
        
        path = [j, nxt]
        cost = fine_graph[j][nxt]
        prev, curr = j, nxt
        while curr not in junction_nodes and len(fine_graph[curr]) == 2:
            adj = list(fine_graph[curr].keys())
            next_step = adj[0] if adj[0] != prev else adj[1]
            visited_edges.add(tuple(sorted([curr, next_step])))
            path.append(next_step)
            cost += fine_graph[curr][next_step]
            prev, curr = curr, next_step
            
        dest = curr
        if dest != j:
            if dest not in junction_graph[j] or cost < junction_graph[j][dest][0]:
                junction_graph[j][dest] = (cost, path)
            if j not in junction_graph[dest] or cost < junction_graph[dest][j][0]:
                junction_graph[dest][j] = (cost, path[::-1])

print(f"Junction graph built: {len(junction_graph)} nodes, {sum(len(v) for v in junction_graph.values()) // 2} condensed edges.")

def route_osm_track(p1, p2):
    """Finds exact physical track centerline between two coordinates using junction graph."""
    n1 = find_nearest_fine_node(p1)
    n2 = find_nearest_fine_node(p2)
    
    if not n1 or not n2 or n1 == n2:
        return [p1, p2]
        
    straight_d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    pq = [(straight_d, 0.0, n1, [n1])]
    visited = {}
    
    while pq:
        est, cost, curr, path = heapq.heappop(pq)
        if curr == n2:
            if cost > 2.5 * straight_d and straight_d > 0.15:
                return [p1, p2]
            full_geom = [p1]
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                edge_geom = junction_graph[u][v][1]
                for pt in edge_geom:
                    if not full_geom or pt != full_geom[-1]:
                        full_geom.append(pt)
            if full_geom[-1] != p2:
                full_geom.append(p2)
            return full_geom
            
        if curr in visited and visited[curr] <= cost:
            continue
        visited[curr] = cost
        
        for neighbor, (weight, _) in junction_graph[curr].items():
            new_cost = cost + weight
            if neighbor not in visited or new_cost < visited[neighbor]:
                h = math.hypot(n2[0] - neighbor[0], n2[1] - neighbor[1])
                heapq.heappush(pq, (new_cost + h, new_cost, neighbor, path + [neighbor]))
                
    return [p1, p2]

# 5. Accurate Swedish Train Categorization Function
def categorize_swedish_train(agency_name, short_name, long_name, trip_id_or_num):
    agency_low = (agency_name or '').lower()
    comb = f"{agency_name} {short_name} {long_name}".lower()

    # 1. High Speed operators
    if 'arlanda express' in comb or 'mtrx' in comb or 'mtr express' in comb or 'vr snabb' in comb:
        return 'highspeed'

    # 2. Explicit Night Trains
    if 'nattåg' in comb or 'nattag' in comb:
        return 'night'

    # 3. InterCity operators
    if 'öresundståg' in comb or 'oresundstag' in comb or agency_name == '110':
        return 'intercity'
    if 'snälltåget' in comb or 'snalltaget' in comb:
        return 'intercity'
    if 'tågab' in comb or 'tagab' in comb:
        return 'intercity'

    # 4. SJ AB specifics based on train number series
    if 'sj' in agency_low:
        num = None
        try:
            num = int(trip_id_or_num)
        except (ValueError, TypeError):
            pass
        if num is not None:
            # Night trains: 1-2 (Berlin/Hamburg), 91-98 (Luleå/Narvik), 3900-3903
            if num in (1, 2, 91, 92, 93, 94, 95, 96, 97, 98, 3900, 3901, 3902, 3903):
                return 'night'
            # SJ Snabbtåg (X2000 / SJ 3000): 400-699, 50-89, 100-199, 10400-10699, 10500-10699
            if (400 <= num <= 699) or (50 <= num <= 89) or (100 <= num <= 199) or (10400 <= num <= 10699):
                return 'highspeed'
            # SJ InterCity: 20-49, 200-299, 10200-10299
            if (20 <= num <= 49) or (200 <= num <= 299) or (10200 <= num <= 10299):
                return 'intercity'
        return 'regional'

    # 5. Vy Tåg specifics
    if 'vy' in agency_low:
        num = None
        try: num = int(trip_id_or_num)
        except: pass
        if num is not None and num in (91, 92, 93, 94, 95, 96):
            return 'night'
        return 'regional'

    # 6. Default regional operators (SL, Pågatåg, Mälartåg, Västtrafik, TiB, Krösatågen, Norrtåg, Östgötapendeln, etc.)
    return 'regional'

def clean_station_name(name):
    for suffix in [" Centralstation", " central", " station", " resecentrum", " tågstation", " Jvstn", " C"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()

def clean_trip_id(tid):
    if tid.startswith("740") and len(tid) >= 6:
        core = tid[3:6]
        if core.isdigit():
            return str(int(core))
    return tid

def parse_time_to_seconds(time_str):
    if not time_str: return None
    parts = time_str.strip().split(':')
    if len(parts) >= 2:
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2]) if len(parts) > 2 else 0
        return h * 3600 + m * 60 + s
    return None

all_weekly_corridors = []

def rdp_simplify(pts, epsilon=0.0018):
    """Ramer-Douglas-Peucker algorithm for curve simplification (preserving sharp bends & lake curves)."""
    if len(pts) <= 2:
        return pts
    p1, p2 = pts[0], pts[-1]
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    norm = math.hypot(dx, dy)
    dmax = 0.0
    index = 0
    for i in range(1, len(pts) - 1):
        if norm == 0:
            d = math.hypot(pts[i][0] - p1[0], pts[i][1] - p1[1])
        else:
            d = abs(dy * pts[i][0] - dx * pts[i][1] + p2[0]*p1[1] - p2[1]*p1[0]) / norm
        if d > dmax:
            index = i
            dmax = d
    if dmax > epsilon:
        r1 = rdp_simplify(pts[:index+1], epsilon)
        r2 = rdp_simplify(pts[index:], epsilon)
        return r1[:-1] + r2
    else:
        return [p1, p2]

# 6. Generate Full 7-Day Timetables (Option B: Full OSM & Option C: Compact RDP OSM)
print("\n--- Generating Full 7-Day Timetables (Option B & Option C) ---")

with zipfile.ZipFile(ZIP_PATH, 'r') as z:
    agencies = {}
    with z.open('agency.txt') as f:
        for r in csv.DictReader(f.read().decode('utf-8-sig').splitlines()):
            a_name = r['agency_name'].strip()
            if a_name == '110' or r.get('agency_id') == '500000000000000110':
                a_name = 'Öresundståg'
            agencies[r['agency_id']] = a_name

    rail_routes = {}
    with z.open('routes.txt') as f:
        for r in csv.DictReader(f.read().decode('utf-8-sig').splitlines()):
            if r.get('route_type') in ('1', '2', '100', '101', '102', '103', '104', '105', '106', '107', '108'):
                agency = agencies.get(r.get('agency_id', ''), '')
                comb = f"{agency} {r.get('route_short_name', '')} {r.get('route_long_name', '')}".lower()
                if 'ersättning' not in comb and 'ersattning' not in comb:
                    rail_routes[r['route_id']] = (agency or 'Tåg', r.get('route_short_name', ''), r.get('route_long_name', ''))

    stops = {}
    with z.open('stops.txt') as f:
        for r in csv.DictReader(f.read().decode('utf-8-sig').splitlines()):
            try:
                s_id = r['stop_id']
                s_name = r['stop_name']
                lon = float(r['stop_lon'])
                lat = float(r['stop_lat'])

                # 1. Coordinate Sanitizer: Fix known upstream GTFS typos
                if 'Väse' in s_name or 'Vse' in s_name or s_id == '9022050000287004':
                    lon, lat = 13.7845, 59.3995

                # 2. Geographic Boundary Sanitizer: Sweden/Nordic rail bounds
                if 54.0 <= lat <= 71.5 and 8.0 <= lon <= 26.0:
                    stops[s_id] = (round(lon, 4), round(lat, 4), s_name)
            except ValueError:
                continue

    all_trips_meta = {}
    with z.open('trips.txt') as f:
        for r in csv.DictReader(f.read().decode('utf-8-sig').splitlines()):
            rid = r['route_id']
            if rid in rail_routes:
                op, r_short, r_long = rail_routes[rid]
                raw_name = r.get('trip_short_name') or r.get('trip_headsign') or r.get('samtrafiken_internal_trip_number') or r['trip_id']
                clean_name = clean_trip_id(raw_name)
                cls = categorize_swedish_train(op, r_short, r_long, clean_name)
                
                all_trips_meta[r['trip_id']] = {
                    'route_id': rid,
                    'service_id': r['service_id'],
                    'name': clean_name,
                    'op': op,
                    'cls': cls
                }

    stop_times_by_trip = defaultdict(list)
    with z.open('stop_times.txt') as f:
        for r in csv.DictReader(f.read().decode('utf-8-sig').splitlines()):
            tid = r['trip_id']
            if tid in all_trips_meta:
                t_dep = parse_time_to_seconds(r.get('departure_time') or r.get('arrival_time'))
                try:
                    seq = int(r['stop_sequence'])
                    stop_times_by_trip[tid].append((seq, r['stop_id'], t_dep))
                except ValueError:
                    continue

    for tid in stop_times_by_trip:
        stop_times_by_trip[tid].sort(key=lambda x: x[0])

    target_dates = [
        ("20260831", "mon"),
        ("20260901", "tue"),
        ("20260902", "wed"),
        ("20260903", "thu"),
        ("20260904", "fri"),
        ("20260905", "sat"),
        ("20260906", "sun")
    ]

    service_calendar = {}
    with z.open('calendar.txt') as f:
        for r in csv.DictReader(f.read().decode('utf-8-sig').splitlines()):
            service_calendar[r['service_id']] = {
                'days': [int(r[d]) for d in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']],
                'start': r.get('start_date', '20000101'),
                'end': r.get('end_date', '20991231')
            }

    calendar_exceptions = defaultdict(dict)
    if 'calendar_dates.txt' in z.namelist():
        with z.open('calendar_dates.txt') as f:
            for r in csv.DictReader(f.read().decode('utf-8-sig').splitlines()):
                calendar_exceptions[r['date']][r['service_id']] = int(r['exception_type'])

    osm_route_cache = {}

    for date_str, short_name in target_dates:
        target_dt = datetime.strptime(date_str, "%Y%m%d")
        w_idx = target_dt.weekday()
        weekday_name = target_dt.strftime("%A")
        formatted_date = target_dt.strftime("%Y-%m-%d")

        active_trips = []
        for tid, tmeta in all_trips_meta.items():
            sid = tmeta['service_id']
            is_active = False
            if sid in calendar_exceptions[date_str]:
                if calendar_exceptions[date_str][sid] == 1: is_active = True
            elif sid in service_calendar:
                cal = service_calendar[sid]
                if cal['start'] <= date_str <= cal['end'] and cal['days'][w_idx] == 1:
                    is_active = True
            if is_active:
                active_trips.append(tid)

        trips_out_b = []
        trips_out_c = []
        category_counts = defaultdict(int)

        for tid in active_trips:
            trip_meta = all_trips_meta[tid]
            st_list = stop_times_by_trip.get(tid, [])
            if len(st_list) < 2:
                continue

            raw_stops_with_times = []
            for seq, s_id, t in st_list:
                if s_id in stops and t is not None:
                    lon, lat, _ = stops[s_id]
                    raw_stops_with_times.append((lon, lat, t))

            if len(raw_stops_with_times) < 2:
                continue

            # Speed Anomaly Rejection: Filter out impossible speed jumps (> 350 km/h)
            stops_with_times = [raw_stops_with_times[0]]
            for next_st in raw_stops_with_times[1:]:
                prev_st = stops_with_times[-1]
                dt = next_st[2] - prev_st[2]
                d_deg = math.hypot(next_st[0] - prev_st[0], next_st[1] - prev_st[1])
                if dt > 0:
                    speed_kmh = (d_deg * 111.0) / (dt / 3600.0)
                    if speed_kmh > 350.0 and d_deg > 0.5:
                        continue
                stops_with_times.append(next_st)

            if len(stops_with_times) < 2:
                continue

            raw_pts = []
            for i in range(len(stops_with_times) - 1):
                p1 = (stops_with_times[i][0], stops_with_times[i][1])
                p2 = (stops_with_times[i+1][0], stops_with_times[i+1][1])
                t1 = stops_with_times[i][2]
                t2 = stops_with_times[i+1][2]
                dt = t2 - t1
                if dt <= 0:
                    continue

                pair_key = (p1, p2)
                if pair_key not in osm_route_cache:
                    osm_route_cache[pair_key] = route_osm_track(p1, p2)
                segment = osm_route_cache[pair_key]

                cum_dists = [0.0]
                for k in range(len(segment) - 1):
                    d = math.hypot(segment[k+1][0] - segment[k][0], segment[k+1][1] - segment[k][1])
                    cum_dists.append(cum_dists[-1] + d)
                total_d = cum_dists[-1]

                for k in range(len(segment) - 1):
                    frac = (cum_dists[k] / total_d) if total_d > 0 else (k / float(len(segment)))
                    t = int(t1 + dt * frac)
                    if 0 <= t < 86400:
                        raw_pts.append([round(segment[k][0], 4), round(segment[k][1], 4), t])

            last_lon, last_lat, last_t = stops_with_times[-1]
            if 0 <= last_t < 86400:
                raw_pts.append([round(last_lon, 4), round(last_lat, 4), int(last_t)])

            if len(raw_pts) >= 2:
                # Option B points: 200m downsampling
                pts_b = [raw_pts[0]]
                for pt in raw_pts[1:-1]:
                    prev = pts_b[-1]
                    if (pt[2] - prev[2] >= 20) or math.hypot(pt[0] - prev[0], pt[1] - prev[1]) >= 0.002:
                        pts_b.append(pt)
                pts_b.append(raw_pts[-1])

                # Option C points: RDP curve simplification (~200m tolerance)
                pts_c = rdp_simplify(raw_pts, epsilon=0.0018)

                cls = trip_meta['cls']
                category_counts[cls] += 1
                origin_name = stops.get(st_list[0][1], (0, 0, ''))[2]
                dest_name = stops.get(st_list[-1][1], (0, 0, ''))[2]

                clean_from = clean_station_name(origin_name)
                clean_to = clean_station_name(dest_name)

                trips_out_b.append({
                    "id": trip_meta['name'],
                    "op": trip_meta['op'],
                    "cls": cls,
                    "from": clean_from,
                    "to": clean_to,
                    "pts": pts_b
                })

                trips_out_c.append({
                    "id": trip_meta['name'],
                    "op": trip_meta['op'],
                    "cls": cls,
                    "from": clean_from,
                    "to": clean_to,
                    "pts": pts_c
                })
                
                all_weekly_corridors.append([(p[0], p[1]) for p in pts_b])

        # Save Option B
        out_b = {
            "date": formatted_date,
            "weekday": weekday_name,
            "counts": category_counts,
            "trips": trips_out_b
        }
        out_fname_b = f"sweden-trains-{short_name}-osm.json"
        out_fpath_b = os.path.join(DATA_DIR, out_fname_b)
        with open(out_fpath_b, 'w', encoding='utf-8') as f:
            json.dump(out_b, f, separators=(',', ':'))

        # Save Option C (Compact RDP)
        out_c = {
            "date": formatted_date,
            "weekday": weekday_name,
            "counts": category_counts,
            "trips": trips_out_c
        }
        out_fname_c = f"sweden-trains-{short_name}-compact.json"
        out_fpath_c = os.path.join(DATA_DIR, out_fname_c)
        with open(out_fpath_c, 'w', encoding='utf-8') as f:
            json.dump(out_c, f, separators=(',', ':'))

        sz_b = os.path.getsize(out_fpath_b) / 1024 / 1024
        sz_c = os.path.getsize(out_fpath_c) / 1024 / 1024
        print(f"  {formatted_date} ({weekday_name}): {len(trips_out_b)} trips -> Opt B: {sz_b:.1f} MB | Opt C (RDP Compact): {sz_c:.2f} MB [HS: {category_counts['highspeed']}, IC: {category_counts['intercity']}, Reg: {category_counts['regional']}, Night: {category_counts['night']}]")

# 7. Build sweden-geo.json with Active OSM Tracks and Realistic Geographic Urban Footprints
print("\n--- Generating Clean data/sweden-geo.json ---")
with open(os.path.join(DATA_DIR, "sweden-geo.json"), 'r', encoding='utf-8') as f:
    base_geo = json.load(f)

osm_landuse_path = os.path.join(DATA_DIR, "osm", "sweden-urban-osm-landuse.json")
if os.path.exists(osm_landuse_path):
    with open(osm_landuse_path, 'r', encoding='utf-8') as f:
        osm_landuse = json.load(f)
    core_urban = osm_landuse.get('core_urban', [])
    semi_urban = osm_landuse.get('semi_urban', [])
else:
    core_urban = []
    semi_urban = []

print(f"Loaded {len(core_urban)} true OpenStreetMap urban landuse polygons.")

grid_edges = set()
track_segments = []

for line in all_weekly_corridors:
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
clean_osm_tracks = []

for seg in track_segments:
    p1 = (seg[0][0], seg[0][1])
    p2 = (seg[1][0], seg[1][1])
    edge = tuple(sorted([p1, p2]))
    if edge in visited_edges:
        continue

    line = [list(p1), list(p2)]
    visited_edges.add(edge)

    curr, prev = p2, p1
    while len(adj[curr]) == 2:
        nxt = adj[curr][0] if adj[curr][0] != prev else adj[curr][1]
        next_edge = tuple(sorted([curr, nxt]))
        if next_edge in visited_edges: break
        visited_edges.add(next_edge)
        line.append(list(nxt))
        prev, curr = curr, nxt

    curr, prev = p1, p2
    while len(adj[curr]) == 2:
        nxt = adj[curr][0] if adj[curr][0] != prev else adj[curr][1]
        next_edge = tuple(sorted([curr, nxt]))
        if next_edge in visited_edges: break
        visited_edges.add(next_edge)
        line.insert(0, list(nxt))
        prev, curr = curr, nxt

    clean_osm_tracks.append(line)

geo_osm = {
    "outline": base_geo.get("outline", []),
    "states": base_geo.get("states", []),
    "lakes": base_geo.get("lakes", []),
    "city_limits": core_urban,
    "core_urban": core_urban,
    "semi_urban": semi_urban,
    "tracks": clean_osm_tracks
}

with open(os.path.join(DATA_DIR, "sweden-geo.json"), 'w', encoding='utf-8') as f:
    json.dump(geo_osm, f, separators=(',', ':'))

print(f"Saved data/sweden-geo.json ({len(clean_osm_tracks)} active clean curved tracks, {len(core_urban)} urban footprints, {os.path.getsize(os.path.join(DATA_DIR, 'sweden-geo.json'))/1024:.1f} KB).")
print("\n=== Generation Completed Successfully! ===")
