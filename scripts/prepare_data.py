import os
import zipfile
import csv
import json
import io
import math
import heapq
from datetime import datetime, timedelta
from collections import defaultdict

# Comprehensive High-Resolution Swedish Railway Corridors (every station & junction)
# Comprehensive High-Resolution Swedish Railway Corridors (every station & junction)
CORRIDORS = [
    # 1. Västra stambanan (Stockholm - Göteborg via Södertälje, Gnesta, Flen, Katrineholm, Hallsberg, Laxå, Skövde, Falköping, Herrljunga, Alingsås)
    [
        (18.058, 59.330), (18.062, 59.314), (18.011, 59.279), (17.948, 59.219), (17.628, 59.196),
        (17.575, 59.088), (17.311, 59.049), (17.039, 59.030), (16.782, 59.027), (16.589, 59.058),
        (16.208, 58.996), (15.932, 59.043), (15.548, 59.017), (15.111, 59.066), (14.812, 59.032),
        (14.618, 58.987), (14.398, 58.878), (14.129, 58.706), (13.985, 58.552), (13.855, 58.390),
        (13.702, 58.283), (13.557, 58.172), (13.298, 58.125), (13.024, 58.077), (12.810, 58.034),
        (12.533, 57.929), (12.358, 57.818), (12.270, 57.771), (12.105, 57.739), (11.973, 57.708)
    ],
    # 2. Södra stambanan & Nyköpingsbanan (Stockholm - Malmö via Södertälje, Nyköping, Norrköping, Linköping, Mjölby, Tranås, Nässjö, Sävsjö, Alvesta, Älmhult, Hässleholm, Lund)
    [
        (18.058, 59.330), (18.062, 59.314), (18.011, 59.279), (17.948, 59.219), (17.628, 59.196),
        (17.575, 59.088), (17.514, 58.962), (17.311, 58.903), (17.012, 58.753), (16.568, 58.682),
        (16.321, 58.643), (16.183, 58.596), (15.902, 58.508), (15.626, 58.416), (15.378, 58.371),
        (15.127, 58.324), (14.978, 58.037), (14.811, 57.842), (14.697, 57.653), (14.664, 57.401),
        (14.556, 56.899), (14.412, 56.721), (14.138, 56.551), (13.996, 56.380), (13.764, 56.158),
        (13.541, 55.932), (13.303, 55.838), (13.187, 55.707), (13.061, 55.639), (13.000, 55.609)
    ],
    # 3. Västkustbanan (Göteborg - Malmö via Kungsbacka, Varberg, Falkenberg, Halmstad, Laholm, Båstad, Ängelholm, Helsingborg, Landskrona, Lund)
    [
        (11.973, 57.708), (12.015, 57.655), (12.079, 57.487), (12.181, 57.282), (12.249, 57.111),
        (12.421, 57.012), (12.511, 56.913), (12.712, 56.782), (12.865, 56.670), (13.045, 56.516),
        (12.876, 56.425), (12.860, 56.248), (12.752, 56.141), (12.698, 56.044), (12.782, 55.952),
        (12.860, 55.867), (12.982, 55.812), (13.109, 55.792), (13.187, 55.707), (13.061, 55.639), (13.000, 55.609)
    ],
    # 4. Norge/Vänerbanan (Göteborg - Trollhättan - Öxnered - Mellerud - Åmål - Säffle - Grums - Kil - Karlstad)
    [
        (11.973, 57.708), (12.008, 57.728), (12.032, 57.882), (12.138, 58.032), (12.296, 58.284),
        (12.278, 58.378), (12.458, 58.702), (12.705, 59.052), (12.928, 59.132), (13.108, 59.258),
        (13.315, 59.505), (13.499, 59.378), (14.108, 59.309)
    ],
    # 5. Mälarbanan (Stockholm - Sundbyberg - Bålsta - Enköping - Västerås - Köping - Arboga - Örebro)
    [
        (18.058, 59.330), (17.968, 59.361), (17.892, 59.412), (17.658, 59.518), (17.531, 59.569),
        (17.082, 59.641), (16.552, 59.607), (16.208, 59.552), (15.998, 59.510), (15.839, 59.394),
        (15.421, 59.312), (15.212, 59.278)
    ],
    # 6. Svealandsbanan (Stockholm - Södertälje - Nykvarn - Mariefred - Strängnäs - Eskilstuna - Kolbäck - Arboga)
    [
        (18.058, 59.330), (17.628, 59.196), (17.432, 59.182), (17.212, 59.261), (17.032, 59.378),
        (16.508, 59.371), (16.221, 59.442), (15.839, 59.394)
    ],
    # 7. Ostkustbanan & Botniabanan (Stockholm - Arlanda - Uppsala - Gävle - Söderhamn - Sundsvall - Härnösand - Örnsköldsvik - Umeå)
    [
        (18.058, 59.330), (17.998, 59.428), (17.902, 59.532), (17.929, 59.649), (17.812, 59.721),
        (17.646, 59.858), (17.582, 60.112), (17.514, 60.344), (17.382, 60.521), (17.151, 60.676),
        (17.060, 61.304), (17.108, 61.725), (17.315, 62.387), (17.938, 62.632), (18.718, 63.291), (20.266, 63.829)
    ],
    # 8. Dalabanan (Uppsala - Sala - Avesta Krylbo - Borlänge - Falun - Rättvik - Mora)
    [
        (17.646, 59.858), (16.912, 59.932), (16.608, 59.921), (16.192, 60.142), (15.982, 60.278),
        (15.752, 60.351), (15.432, 60.485), (15.636, 60.603), (15.021, 60.882), (14.542, 61.008)
    ],
    # 9. Bergslagsbanan (Gävle - Sandviken - Storvik - Hofors - Falun - Borlänge - Ludvika - Grängesberg - Ställdalen - Kopparberg - Lindesberg - Frövi - Örebro - Hallsberg)
    [
        (17.151, 60.676), (16.782, 60.618), (16.538, 60.582), (16.266, 60.569), (15.636, 60.603),
        (15.432, 60.485), (15.182, 60.152), (15.008, 60.078), (14.942, 59.932), (15.221, 59.602),
        (15.378, 59.462), (15.212, 59.278), (15.111, 59.066)
    ],
    # 10. Godsstråket (Mjölby - Skänninge - Motala - Degerön - Hallsberg)
    [
        (15.127, 58.324), (15.088, 58.396), (15.048, 58.537), (15.142, 58.782), (15.111, 59.066)
    ],
    # 11. Värmlandsbanan (Hallsberg - Laxå - Degerfors - Kristinehamn - Karlstad - Kil - Arvika - Charlottenberg - Kongsvinger - Oslo)
    [
        (15.111, 59.066), (14.618, 58.987), (14.432, 59.237), (14.108, 59.309), (13.821, 59.351),
        (13.499, 59.378), (13.315, 59.505), (12.982, 59.582), (12.592, 59.654), (12.296, 59.883),
        (11.982, 60.012), (11.508, 60.082), (11.082, 59.982), (10.752, 59.911)
    ],
    # 12. Fryksdalsbanan (Kil - Sunne - Lysvik - Torsby)
    [
        (13.315, 59.505), (13.252, 59.682), (13.109, 59.838), (13.121, 60.021), (13.008, 60.138)
    ],
    # 13. Kust till kust (Göteborg - Borås - Alvesta - Växjö - Emmaboda - Kalmar)
    [
        (11.973, 57.708), (12.421, 57.682), (12.936, 57.720), (13.412, 57.551), (14.041, 57.185),
        (14.556, 56.899), (14.807, 56.877), (15.221, 56.742), (15.541, 56.631), (15.908, 56.744), (16.358, 56.662)
    ],
    # 14. Blekinge kustbana (Hässleholm - Kristianstad - Sölvesborg - Karlshamn - Ronneby - Karlskrona)
    [
        (13.764, 56.158), (14.159, 56.033), (14.586, 56.052), (14.862, 56.173), (15.281, 56.208), (15.586, 56.166)
    ],
    # 15. Mittbanan (Sundsvall - Ånge - Östersund - Åre - Storlien - Trondheim)
    [
        (17.315, 62.387), (16.920, 62.484), (15.656, 62.997), (14.982, 63.082), (14.636, 63.176),
        (13.982, 63.321), (13.042, 63.417), (12.016, 63.316), (11.104, 63.461), (10.395, 63.430)
    ],
    # 16. Malmbanan (Luleå / Boden - Gällivare - Kiruna - Abisko - Riksgränsen - Narvik)
    [
        (22.165, 65.584), (21.688, 65.825), (20.660, 67.133), (20.222, 67.869),
        (18.831, 68.349), (18.121, 68.430), (17.427, 68.438)
    ],
    # 17. Skåne Banor (Ystad / Simrishamn, Trelleborg, Öresundsbron)
    [
        (13.000, 55.609), (12.982, 55.578), (12.971, 55.562), (13.082, 55.542), (13.232, 55.482),
        (13.512, 55.472), (13.826, 55.430), (14.041, 55.548), (14.351, 55.556)
    ],
    [
        (13.000, 55.609), (12.982, 55.578), (12.971, 55.562), (13.112, 55.482), (13.158, 55.375)
    ],
    [
        (13.000, 55.609), (12.982, 55.578), (12.971, 55.562), (12.752, 55.578), (12.651, 55.628), (12.568, 55.672)
    ],
    # 18. Haparandabanan (Boden - Kalix - Haparanda)
    [
        (21.688, 65.825), (22.582, 65.852), (23.143, 65.865), (24.132, 65.828)
    ]
]

# Build connected railway network graph for topological routing
RAIL_GRAPH = defaultdict(dict)
for c in CORRIDORS:
    for i in range(len(c) - 1):
        p1 = (round(c[i][0], 4), round(c[i][1], 4))
        p2 = (round(c[i+1][0], 4), round(c[i+1][1], 4))
        d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if p2 not in RAIL_GRAPH[p1] or d < RAIL_GRAPH[p1][p2]:
            RAIL_GRAPH[p1][p2] = d
        if p1 not in RAIL_GRAPH[p2] or d < RAIL_GRAPH[p2][p1]:
            RAIL_GRAPH[p2][p1] = d

ALL_GRAPH_NODES = list(RAIL_GRAPH.keys())
for i in range(len(ALL_GRAPH_NODES)):
    n1 = ALL_GRAPH_NODES[i]
    for j in range(i + 1, len(ALL_GRAPH_NODES)):
        n2 = ALL_GRAPH_NODES[j]
        d = math.hypot(n2[0] - n1[0], n2[1] - n1[1])
        if d < 0.04: # connect nearby junctions (< 4 km)
            if n2 not in RAIL_GRAPH[n1] or d < RAIL_GRAPH[n1][n2]:
                RAIL_GRAPH[n1][n2] = d
            if n1 not in RAIL_GRAPH[n2] or d < RAIL_GRAPH[n2][n1]:
                RAIL_GRAPH[n2][n1] = d

def find_corridor_waypoints(p1, p2):
    """Finds smooth curved railway path between two distant points via the topological rail graph.
    If points are already close (< 24 km), returns direct connection without detour."""
    straight_d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if straight_d < 0.22:
        return [p1, p2]
    
    best_n1 = min(ALL_GRAPH_NODES, key=lambda n: math.hypot(n[0] - p1[0], n[1] - p1[1]))
    best_n2 = min(ALL_GRAPH_NODES, key=lambda n: math.hypot(n[0] - p2[0], n[1] - p2[1]))
    
    d1 = math.hypot(best_n1[0] - p1[0], best_n1[1] - p1[1])
    d2 = math.hypot(best_n2[0] - p2[0], best_n2[1] - p2[1])
    
    if d1 > 0.25 or d2 > 0.25:
        return [p1, p2]
    
    if best_n1 == best_n2:
        return [p1, p2]
        
    pq = [(0.0, best_n1, [best_n1])]
    visited = {}
    
    while pq:
        cost, curr, path = heapq.heappop(pq)
        if curr == best_n2:
            if cost > 2.0 * straight_d:
                return [p1, p2]
            out = []
            if math.hypot(path[0][0] - p1[0], path[0][1] - p1[1]) > 0.01:
                out.append(p1)
            out.extend(path)
            if math.hypot(path[-1][0] - p2[0], path[-1][1] - p2[1]) > 0.01:
                out.append(p2)
            return out
            
        if curr in visited and visited[curr] <= cost:
            continue
        visited[curr] = cost
        
        for neighbor, weight in RAIL_GRAPH[curr].items():
            new_cost = cost + weight
            if neighbor not in visited or new_cost < visited[neighbor]:
                heapq.heappush(pq, (new_cost, neighbor, path + [neighbor]))
                
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
        return h * 3600 + m * 60 + s
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

        if idx2 > idx1 and (idx2 - idx1) >= 2:
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

        step_stride = 1
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

        if shape_pts and len(shape_pts) >= 12:
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

                step_stride = 1
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

        # 2. Parse routes (Filter for Rail, excluding replacement buses)
        rail_routes = {}
        with z.open('routes.txt') as f:
            reader = csv.DictReader(f.read().decode('utf-8-sig').splitlines())
            for row in reader:
                r_type = row.get('route_type', '').strip()
                if r_type in ('1', '2', '100', '101', '102', '103', '104', '105', '106', '107', '108'):
                    agency_name = agencies.get(row.get('agency_id', ''), 'Swedish Rail')
                    short_name = row.get('route_short_name', '')
                    long_name = row.get('route_long_name', '')
                    comb = f"{agency_name} {short_name} {long_name}".lower()
                    if 'ersättning' in comb or 'ersattning' in comb:
                        continue
                    rail_routes[row['route_id']] = {
                        'agency_id': row.get('agency_id', ''),
                        'short_name': short_name,
                        'long_name': long_name,
                        'agency_name': agency_name
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
