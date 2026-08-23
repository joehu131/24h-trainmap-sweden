import json
import glob
import math

for fpath in glob.glob("data/sweden-trains-*.json"):
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"\nChecking {fpath} ({len(data['trips'])} trips)...")
    out_of_bounds = []
    huge_jumps = []
    
    for tr in data["trips"]:
        pts = tr["pts"]
        for i, pt in enumerate(pts):
            lon, lat, t = pt
            # Check for bad coordinates
            if not (8.0 <= lon <= 26.0 and 54.5 <= lat <= 70.0):
                out_of_bounds.append((tr["id"], tr["op"], tr["cls"], pt))
                
            if i > 0:
                prev_lon, prev_lat, prev_t = pts[i-1]
                # Distance in deg
                dist = math.hypot(lon - prev_lon, lat - prev_lat)
                dt = t - prev_t
                if dist > 1.5 and dt < 600: # jump > 1.5 deg in < 10 mins is impossible (> 1000 km/h)
                    huge_jumps.append((tr["id"], tr["op"], tr["cls"], pts[i-1], pt, dist, dt))

    if out_of_bounds:
        print(f"  FOUND {len(out_of_bounds)} out-of-bounds points:")
        for o in out_of_bounds[:10]:
            print(f"    {o}")
            
    if huge_jumps:
        print(f"  FOUND {len(huge_jumps)} huge teleportation jumps:")
        for j in huge_jumps[:10]:
            print(f"    {j[0]} ({j[1]} - {j[2]}): from {j[3]} to {j[4]} dist={j[5]:.2f}deg dt={j[6]}s")
            
    if not out_of_bounds and not huge_jumps:
        print("  All points clean.")
