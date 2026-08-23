import os
import zipfile
import csv
import json
import io
import math
from datetime import datetime, timedelta
from collections import defaultdict

# Major Swedish Railway Corridors (Trunk network waypoints)
CORRIDORS = [
    # Västra stambanan (Stockholm - Göteborg via Södertälje, Katrineholm, Hallsberg, Laxå, Töreboda, Skövde, Falköping, Herrljunga, Alingsås)
    [(18.058, 59.330), (17.628, 59.196), (16.589, 59.058), (16.208, 58.996), (15.932, 59.043), (15.111, 59.066), (14.618, 58.987), (14.129, 58.706), (13.855, 58.390), (13.557, 58.172), (13.024, 58.077), (12.810, 58.034), (12.533, 57.929), (11.973, 57.708)],
    # Södra stambanan (Stockholm - Malmö via Norrköping, Linköping, Mjölby, Tranås, Nässjö, Sävsjö, Alvesta, Älmhult, Hässleholm, Lund)
    [(18.058, 59.330), (17.628, 59.196), (16.208, 58.996), (16.183, 58.596), (15.626, 58.416), (15.127, 58.324), (14.978, 58.037), (14.697, 57.653), (14.664, 57.401), (14.556, 56.899), (14.138, 56.551), (13.996, 56.380), (13.764, 56.158), (13.303, 55.838), (13.187, 55.707), (13.000, 55.609)],
    # Västkustbanan (Göteborg - Malmö via Varberg, Falkenberg, Halmstad, Laholm, Båstad, Ängelholm, Helsingborg, Landskrona, Lund)
    [(11.973, 57.708), (12.079, 57.487), (12.249, 57.111), (12.511, 56.913), (12.865, 56.670), (13.045, 56.516), (12.876, 56.425), (12.860, 56.248), (12.698, 56.044), (12.860, 55.867), (13.109, 55.792), (13.187, 55.707), (13.000, 55.609)],
    # Blekinge kustbana (Hässleholm - Kristianstad - Karlshamn - Ronneby - Karlskrona)
    [(13.764, 56.158), (14.159, 56.033), (14.478, 56.074), (14.586, 56.052), (14.862, 56.173), (15.281, 56.208), (15.586, 56.166)],
    # Kust till kust (Göteborg - Borås - Alvesta - Växjö - Emmaboda - Kalmar)
    [(11.973, 57.708), (12.936, 57.720), (14.041, 57.185), (14.556, 56.899), (14.807, 56.877), (15.541, 56.631), (15.908, 56.744), (16.358, 56.662)],
    # Värmlandsbanan (Hallsberg - Degerfors - Karlstad - Kil - Arvika - Charlottenberg - Oslo)
    [(15.111, 59.066), (14.618, 58.987), (14.432, 59.237), (14.108, 59.309), (13.499, 59.378), (13.315, 59.505), (12.592, 59.654), (12.296, 59.883), (10.752, 59.911)],
    # Ostkustbanan (Stockholm - Uppsala - Gävle - Söderhamn - Sundsvall - Umeå)
    [(18.058, 59.330), (17.929, 59.649), (17.646, 59.858), (17.514, 60.344), (17.151, 60.676), (17.060, 61.304), (17.108, 61.725), (17.315, 62.387), (17.938, 62.632), (18.718, 63.291), (20.266, 63.829)],
    # Mälarbanan (Stockholm - Enköping - Västerås - Köping - Arboga - Örebro)
    [(18.058, 59.330), (17.531, 59.569), (17.082, 59.641), (16.552, 59.607), (15.998, 59.510), (15.839, 59.394), (15.212, 59.278)],
    # Malmbanan (Luleå / Boden - Gällivare - Kiruna - Abisko - Riksgränsen - Narvik)
    [(22.165, 65.584), (21.688, 65.825), (20.660, 67.133), (20.222, 67.869), (18.831, 68.349), (18.121, 68.430), (17.427, 68.438)]
]

def find_corridor_waypoints(p1, p2):
    best_corridor = None
    best_i1 = -1
    best_i2 = -1
    min_sum_d = float('inf')
    
    for c in CORRIDORS:
        d1s = [math.hypot(p[0] - p1[0], p[1] - p1[1]) for p in c]
        d2s = [math.hypot(p[0] - p2[0], p[1] - p2[1]) for p in c]
        i1 = min(range(len(c)), key=lambda i: d1s[i])
        i2 = min(range(len(c)), key=lambda i: d2s[i])
        
        if d1s[i1] < 0.28 and d2s[i2] < 0.28 and i1 != i2:
            sum_d = d1s[i1] + d2s[i2]
            if sum_d < min_sum_d:
                min_sum_d = sum_d
                best_corridor = c
                best_i1 = i1
                best_i2 = i2
                
    if best_corridor:
        if best_i1 < best_i2:
            return best_corridor[best_i1 : best_i2 + 1]
        else:
            return best_corridor[best_i2 : best_i1 + 1][::-1]
    return [p1, p2]

# Classification Rules
OPERATOR_RULES = {
    'snälltåget': 'intercity',
    'snalltaget': 'intercity',
    'arlanda express': 'highspeed',
    'arlandabanan': 'highspeed',
    'a-train': 'highspeed',
    'mTRX': 'highspeed',
    'mTR express': 'highspeed',
    'vr snabbtåg': 'highspeed',
    'vy tåg': 'intercity',
    'vy': 'intercity',
    'öresundståg': 'intercity',
    'oresundstag': 'intercity',
    'pågatågen': 'regional',
    'pagatagen': 'regional',
    'ösgötapendeln': 'regional',
    'krösatågen': 'regional',
    'krosatagen': 'regional',
    'västtågen': 'regional',
    'vasttagen': 'regional',
    'tiB': 'regional',
    'tåg i bergslagen': 'regional',
    'mälartåg': 'regional',
    'malartag': 'regional',
    'upptåget': 'regional',
    'x-trafik': 'regional',
    'norrtåg': 'regional',
    'norrtag': 'regional',
    'inlandsbanan': 'regional',
    'vättertåg': 'regional',
}

ROUTE_NAME_RULES = {
    'x 2000': 'highspeed',
    'x2000': 'highspeed',
    'sj 3000': 'highspeed',
    'sj 2000': 'highspeed',
    'snabbtåg': 'highspeed',
    'snabbtag': 'highspeed',
    'arlanda express': 'highspeed',
    'intercity': 'intercity',
    'eurocity': 'intercity',
    'nattåg': 'night',
    'nattag': 'night',
    'euronight': 'night',
    'öresundståg': 'intercity',
    'oresundstag': 'intercity',
    'regionaltåg': 'regional',
    'regionaltag': 'regional',
    'pendeltåg': 'regional',
    'pendeltag': 'regional',
    'pågatåg': 'regional',
    'pagatag': 'regional',
    'krösatåg': 'regional',
    'krosatag': 'regional',
    'mälartåg': 'regional',
    'malartag': 'regional',
}

def classify_train(agency_name, route_short_name, route_long_name, trip_headsign):
    combined = f"{agency_name} {route_short_name} {route_long_name} {trip_headsign}".lower()

    if any(k in combined for k in ['nattåg', 'nattag', 'euronight', 'night train']):
        return 'night'

    if any(k in combined for k in ['x 2000', 'x2000', 'sj 3000', 'sj 2000', 'snabbtåg', 'snabbtag', 'arlanda express', 'vr snabbtåg', 'mtrx']):
        return 'highspeed'

    if 'sj' in combined and ('snabbtåg' in combined or 'x2000' in combined or 'sj 3000' in combined):
        return 'highspeed'

    for op_key, category in OPERATOR_RULES.items():
        if op_key.lower() in combined:
            if category == 'intercity' and 'natt' in combined:
                return 'night'
            return category

    for route_key, category in ROUTE_NAME_RULES.items():
        if route_key.lower() in combined:
            return category

    if 'intercity' in combined or 'sj intercity' in combined or 'ic' in route_short_name.lower().split():
        return 'intercity'

    if 'sj' in agency_name.lower():
        return 'intercity'

    return 'regional'

def parse_time_to_seconds(time_str):
    if not time_str:
        return None
    parts = time_str.strip().split(':')
    if len(parts) != 3:
        return None
    try:
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        return h * 3600 + m * s
    except ValueError:
        return None

def clean_station_name(raw):
    if not raw:
        return ""
    cleaned = raw.replace("Centralstation", "C").replace("centralstation", "C")
    cleaned = cleaned.replace("Central", "C").replace("resecentrum", "").replace("Resecentrum", "")
    cleaned = cleaned.replace(" station", "").replace(" Station", "").replace(" jvstn", "").strip()
    return cleaned

def match_stops_to_shape(shape_pts, stops_with_times):
    """
    Project scheduled stop times onto true GTFS track geometry curves.
    """
    if len(shape_pts) < 2:
        return []

    # Check and align shape orientation
    d0 = (shape_pts[0][0] - stops_with_times[0][0])**2 + (shape_pts[0][1] - stops_with_times[0][1])**2
    d1 = (shape_pts[-1][0] - stops_with_times[0][0])**2 + (shape_pts[-1][1] - stops_with_times[0][1])**2
    if d1 < d0:
        shape_pts = shape_pts[::-1]

    matched_indices = []
    curr_idx = 0
    num_shape_pts = len(shape_pts)

    for s_lon, s_lat, s_time in stops_with_times:
        best_idx = curr_idx
        best_dist = float('inf')
        for j in range(curr_idx, num_shape_pts):
            d = (shape_pts[j][0] - s_lon)**2 + (shape_pts[j][1] - s_lat)**2
            if d < best_dist:
                best_dist = d
                best_idx = j
        matched_indices.append(best_idx)
        curr_idx = best_idx

    pts_out = []
    for i in range(len(stops_with_times) - 1):
        idx1 = matched_indices[i]
        idx2 = matched_indices[i+1]
        t1 = stops_with_times[i][2]
        t2 = stops_with_times[i+1][2]
        dt = t2 - t1
        if dt <= 0:
            continue

        if idx2 > idx1 and (idx2 - idx1) >= 3:
            segment = shape_pts[idx1 : idx2 + 1]
        else:
            # Fall back to trunk corridor waypoints
            p1 = (stops_with_times[i][0], stops_with_times[i][1])
            p2 = (stops_with_times[i+1][0], stops_with_times[i+1][1])
            segment = find_corridor_waypoints(p1, p2)

        cum_dists = [0.0]
        for k in range(len(segment) - 1):
            d = math.hypot(segment[k+1][0] - segment[k][0], segment[k+1][1] - segment[k][1])
            cum_dists.append(cum_dists[-1] + d)
        total_d = cum_dists[-1]

        step_stride = max(1, len(segment) // max(1, int(dt // 60)))
        for k in range(0, len(segment) - 1, step_stride):
            frac = (cum_dists[k] / total_d) if total_d > 0 else (k / float(len(segment)))
            t = int(t1 + dt * frac)
            if 0 <= t < 86400:
                pts_out.append([round(segment[k][0], 4), round(segment[k][1], 4), t])

    last_pt = shape_pts[matched_indices[-1]]
    if 0 <= stops_with_times[-1][2] < 86400:
        pts_out.append([round(last_pt[0], 4), round(last_pt[1], 4), int(stops_with_times[-1][2])])

    return pts_out

def process_day(z, target_date_clean, rail_routes, stops, all_trips_meta, stop_times_by_trip, shapes_dict):
    """Process trips for one specific day using true curved shapes and corridor routing."""
    target_dt = datetime.strptime(target_date_clean, "%Y%m%d")
    target_weekday_idx = target_dt.weekday()
    weekday_name = target_dt.strftime("%A")
    weekday_short = target_dt.strftime("%a").lower()
    formatted_date = target_dt.strftime("%Y-%m-%d")

    file_list = z.namelist()
    service_calendar = {}
    if 'calendar.txt' in file_list:
        with z.open('calendar.txt') as f:
            reader = csv.DictReader(f.read().decode('utf-8-sig').splitlines())
            for row in reader:
                s_id = row['service_id']
                service_calendar[s_id] = {
                    'days': [int(row[d]) for d in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']],
                    'start': row.get('start_date', '20000101'),
                    'end': row.get('end_date', '20991231')
                }

    calendar_exceptions = defaultdict(dict)
    if 'calendar_dates.txt' in file_list:
        with z.open('calendar_dates.txt') as f:
            reader = csv.DictReader(f.read().decode('utf-8-sig').splitlines())
            for row in reader:
                calendar_exceptions[row['date']][row['service_id']] = int(row['exception_type'])

    active_services = set()
    for s_id, s_info in service_calendar.items():
        if s_info['start'] <= target_date_clean <= s_info['end']:
            if s_info['days'][target_weekday_idx] == 1:
                active_services.add(s_id)
                
    if target_date_clean in calendar_exceptions:
        for s_id, ex_type in calendar_exceptions[target_date_clean].items():
            if ex_type == 1:
                active_services.add(s_id)
            elif ex_type == 2 and s_id in active_services:
                active_services.remove(s_id)

    trips_out = []
    category_counts = defaultdict(int)

    for t_id, trip_meta in all_trips_meta.items():
        if trip_meta['service_id'] not in active_services:
            continue

        st_list = stop_times_by_trip.get(t_id, [])
        if len(st_list) < 2:
            continue

        stops_with_times = []
        for seq, s_id, t in st_list:
            if s_id in stops and t is not None:
                lon, lat, _ = stops[s_id]
                stops_with_times.append((lon, lat, t))

        if len(stops_with_times) < 2:
            continue

        shape_id = trip_meta.get('shape_id')
        shape_pts = shapes_dict.get(shape_id)

        if shape_pts and len(shape_pts) >= 10:
            pts = match_stops_to_shape(shape_pts, stops_with_times)
        else:
            # Corridor-guided routing
            pts = []
            for i in range(len(stops_with_times) - 1):
                p1 = (stops_with_times[i][0], stops_with_times[i][1])
                p2 = (stops_with_times[i+1][0], stops_with_times[i+1][1])
                t1 = stops_with_times[i][2]
                t2 = stops_with_times[i+1][2]
                dt = t2 - t1
                if dt <= 0: continue
                
                segment = find_corridor_waypoints(p1, p2)
                cum_dists = [0.0]
                for k in range(len(segment) - 1):
                    d = math.hypot(segment[k+1][0] - segment[k][0], segment[k+1][1] - segment[k][1])
                    cum_dists.append(cum_dists[-1] + d)
                total_d = cum_dists[-1]

                step_stride = max(1, len(segment) // max(1, int(dt // 60)))
                for k in range(0, len(segment) - 1, step_stride):
                    frac = (cum_dists[k] / total_d) if total_d > 0 else (k / float(len(segment)))
                    t = int(t1 + dt * frac)
                    if 0 <= t < 86400:
                        pts.append([round(segment[k][0], 4), round(segment[k][1], 4), t])

            last_lon, last_lat, last_t = stops_with_times[-1]
            if 0 <= last_t < 86400:
                pts.append([round(last_lon, 4), round(last_lat, 4), int(last_t)])

        if len(pts) >= 2:
            cls = trip_meta['cls']
            category_counts[cls] += 1
            
            origin_name = stops.get(st_list[0][1], (0, 0, ''))[2]
            dest_name = stops.get(st_list[-1][1], (0, 0, ''))[2]
            
            trips_out.append({
                "id": trip_meta['name'],
                "op": trip_meta['op'],
                "cls": cls,
                "from": clean_station_name(origin_name),
                "to": clean_station_name(dest_name),
                "pts": pts
            })

    print(f"  {formatted_date} ({weekday_name}): {len(trips_out)} trips (High-Speed: {category_counts['highspeed']}, Intercity: {category_counts['intercity']}, Regional: {category_counts['regional']}, Night: {category_counts['night']})")
    
    return {
        "date": formatted_date,
        "weekday": weekday_name,
        "weekday_short": weekday_short,
        "trips": trips_out
    }

def process_gtfs_full_week(zip_path, start_date_str="20260831"):
    """
    Extract and process a full 7-day week (Monday to Sunday) from GTFS Sweden 3 dataset
    with full track geometry from shapes.txt and trunk corridor routing.
    """
    print(f"Opening GTFS archive: {zip_path}")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as z:
        # 1. Parse agencies
        agencies = {}
        with z.open('agency.txt') as f:
            reader = csv.DictReader(f.read().decode('utf-8-sig').splitlines())
            for row in reader:
                agencies[row['agency_id']] = row['agency_name']

        # 2. Parse routes (Filter for Rail)
        rail_routes = {}
        with z.open('routes.txt') as f:
            reader = csv.DictReader(f.read().decode('utf-8-sig').splitlines())
            for row in reader:
                r_type = row.get('route_type', '').strip()
                if r_type in ('1', '2', '100', '101', '102', '103', '104', '105', '106', '107', '108'):
                    rail_routes[row['route_id']] = {
                        'agency_id': row.get('agency_id', ''),
                        'short_name': row.get('route_short_name', ''),
                        'long_name': row.get('route_long_name', ''),
                        'agency_name': agencies.get(row.get('agency_id', ''), 'Swedish Rail')
                    }
        print(f"Found {len(rail_routes)} rail routes.")

        # 3. Parse stops
        stops = {}
        with z.open('stops.txt') as f:
            reader = csv.DictReader(f.read().decode('utf-8-sig').splitlines())
            for row in reader:
                try:
                    lat = float(row['stop_lat'])
                    lon = float(row['stop_lon'])
                    if 54.5 <= lat <= 70.0 and 9.0 <= lon <= 26.0:
                        stops[row['stop_id']] = (lon, lat, row.get('stop_name', ''))
                except (ValueError, KeyError):
                    continue
        print(f"Loaded {len(stops)} valid Swedish railway stops.")

        # 4. Parse trips and extract needed shape_ids
        all_trips_meta = {}
        needed_shape_ids = set()
        with z.open('trips.txt') as f:
            reader = csv.DictReader(f.read().decode('utf-8-sig').splitlines())
            for row in reader:
                r_id = row['route_id']
                if r_id in rail_routes:
                    r_info = rail_routes[r_id]
                    t_id = row['trip_id']
                    shape_id = row.get('shape_id', '').strip()
                    if shape_id:
                        needed_shape_ids.add(shape_id)

                    cls = classify_train(
                        r_info['agency_name'],
                        r_info['short_name'],
                        r_info['long_name'],
                        row.get('trip_headsign', '')
                    )
                    train_name = row.get('trip_short_name') or row.get('samtrafiken_internal_trip_number') or r_info['short_name'] or t_id[-4:]
                    if not train_name or train_name.strip() == '':
                        train_name = f"Train {t_id[-4:]}"

                    all_trips_meta[t_id] = {
                        'route_id': r_id,
                        'service_id': row['service_id'],
                        'shape_id': shape_id,
                        'name': train_name,
                        'cls': cls,
                        'op': r_info['agency_name']
                    }
        print(f"Mapped metadata for {len(all_trips_meta)} rail trips ({len(needed_shape_ids)} distinct track shapes).")

        # 5. Stream shapes.txt to get true physical railway geometry
        print("Streaming shapes.txt for true rail track curves...")
        raw_shapes = defaultdict(list)
        if 'shapes.txt' in z.namelist():
            with z.open('shapes.txt') as f:
                text_stream = io.TextIOWrapper(f, encoding='utf-8-sig')
                reader = csv.DictReader(text_stream)
                for row in reader:
                    s_id = row['shape_id']
                    if s_id in needed_shape_ids:
                        try:
                            seq = int(row.get('shape_pt_sequence', 0))
                            lon = float(row['shape_pt_lon'])
                            lat = float(row['shape_pt_lat'])
                            if 54.5 <= lat <= 70.0 and 9.0 <= lon <= 26.0:
                                raw_shapes[s_id].append((seq, lon, lat))
                        except (ValueError, KeyError):
                            continue

        shapes_dict = {}
        for s_id, pt_list in raw_shapes.items():
            pt_list.sort(key=lambda x: x[0])
            shapes_dict[s_id] = [(p[1], p[2]) for p in pt_list]
        print(f"Loaded {len(shapes_dict)} high-resolution curved track shapes.")

        # 6. Parse stop_times for all rail trips
        print("Parsing stop times for all rail trips...")
        stop_times_by_trip = defaultdict(list)
        with z.open('stop_times.txt') as f:
            text_stream = io.TextIOWrapper(f, encoding='utf-8-sig')
            reader = csv.DictReader(text_stream)
            for row in reader:
                t_id = row['trip_id']
                if t_id in all_trips_meta:
                    dep = parse_time_to_seconds(row.get('departure_time'))
                    arr = parse_time_to_seconds(row.get('arrival_time'))
                    t = dep if dep is not None else arr
                    seq = int(row.get('stop_sequence', 0))
                    stop_times_by_trip[t_id].append((seq, row['stop_id'], t))

        for t_id in stop_times_by_trip:
            stop_times_by_trip[t_id].sort(key=lambda x: x[0])

        # 7. Generate Full 7 Days (Mon-Sun)
        print("\n--- Generating Full 7-Day Timetables (Mon-Sun) with Curved Track Shapes ---")
        start_dt = datetime.strptime(start_date_str, "%Y%m%d")
        
        for day_offset in range(7):
            current_dt = start_dt + timedelta(days=day_offset)
            date_str = current_dt.strftime("%Y%m%d")
            day_data = process_day(z, date_str, rail_routes, stops, all_trips_meta, stop_times_by_trip, shapes_dict)
            
            day_file = os.path.join(data_dir, f"sweden-trains-{day_data['weekday_short']}.json")
            with open(day_file, 'w', encoding='utf-8') as f_out:
                json.dump(day_data, f_out, separators=(',', ':'))

    print("\nSuccessfully generated 7 daily timetable files with real track curves in data/ directory.")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    zip_path = os.path.join(base_dir, 'data', 'sweden.zip')
    process_gtfs_full_week(zip_path, start_date_str="20260831")
