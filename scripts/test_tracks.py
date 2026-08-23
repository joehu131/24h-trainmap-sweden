import json
import zipfile
import csv
import math
from collections import defaultdict

def generate_clean_rail_network():
    with open('data/sweden-trains-wed.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Collect unique station-to-station corridor segments
    # In each trip, get the endpoints and intermediate waypoints
    unique_edges = set()
    track_lines = []

    # Map of routes to avoid duplicates
    corridors = defaultdict(int)
    
    for tr in data['trips']:
        pts = tr['pts']
        # Group by origin-destination or simplify
        coords = [[p[0], p[1]] for p in pts]
        # Remove consecutive duplicate or near-duplicate points
        cleaned = [coords[0]]
        for pt in coords[1:]:
            prev = cleaned[-1]
            if math.hypot(pt[0] - prev[0], pt[1] - prev[1]) >= 0.01: # ~1km
                cleaned.append(pt)
        if len(cleaned) >= 2:
            key = (cleaned[0][0], cleaned[0][1], cleaned[-1][0], cleaned[-1][1])
            rev = (cleaned[-1][0], cleaned[-1][1], cleaned[0][0], cleaned[0][1])
            if key not in corridors and rev not in corridors:
                corridors[key] = cleaned

    print(f"Extracted {len(corridors)} clean unique rail corridor lines.")
    
    # Merge / clean overlapping segments into single clean lines
    # For every segment in corridors, break down into small grid edges to deduplicate 100%
    grid_edges = set()
    final_segments = []
    
    for line in corridors.values():
        for i in range(len(line) - 1):
            p1 = (round(line[i][0], 3), round(line[i][1], 3))
            p2 = (round(line[i+1][0], 3), round(line[i+1][1], 3))
            if p1 != p2:
                edge = tuple(sorted([p1, p2]))
                if edge not in grid_edges:
                    grid_edges.add(edge)
                    final_segments.append([[p1[0], p1[1]], [p2[0], p2[1]]])

    print(f"Total deduplicated track segments: {len(final_segments)}")
    return final_segments

if __name__ == '__main__':
    generate_clean_rail_network()
