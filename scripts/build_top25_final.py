import json, math, os, glob, time
import shapely
from shapely.geometry import Polygon, MultiPolygon, shape, Point, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

TOP_25_CITIES = [
    ("Stockholm", 59.329, 18.069, 16.0),
    ("Göteborg", 57.709, 11.975, 12.0),
    ("Malmö", 55.605, 13.004, 9.0),
    ("Uppsala", 59.858, 17.639, 7.0),
    ("Västerås", 59.610, 16.545, 6.5),
    ("Örebro", 59.274, 15.207, 6.5),
    ("Linköping", 58.411, 15.622, 6.0),
    ("Helsingborg", 56.046, 12.695, 6.0),
    ("Jönköping", 57.783, 14.162, 6.0),
    ("Norrköping", 58.588, 16.188, 6.0),
    ("Lund", 55.705, 13.191, 5.0),
    ("Umeå", 63.829, 20.266, 5.5),
    ("Gävle", 60.675, 17.141, 5.5),
    ("Borås", 57.720, 12.936, 5.0),
    ("Eskilstuna", 59.371, 16.508, 5.0),
    ("Södertälje", 59.196, 17.628, 5.0),
    ("Halmstad", 56.670, 12.865, 5.0),
    ("Växjö", 56.877, 14.807, 5.0),
    ("Karlstad", 59.379, 13.504, 5.0),
    ("Sundsvall", 62.391, 17.307, 5.0),
    ("Östersund", 63.179, 14.636, 5.0),
    ("Trollhättan", 58.284, 12.296, 4.5),
    ("Luleå", 65.584, 22.165, 5.0),
    ("Borlänge", 60.485, 15.432, 4.5),
    ("Falun", 60.603, 15.636, 4.5),
    ("Oslo", 59.914, 10.752, 14.0),
    ("København", 55.676, 12.568, 14.0)
]

t0 = time.time()
print("=== High-Speed Building Top 25 Cohesive Urban Masses ===")

all_source_geoms = []

# 1. City caches
for f in glob.glob("data/osm/city_*.json"):
    try:
        rings = json.load(open(f, encoding='utf-8'))
        for r in rings:
            if len(r) >= 4:
                p = Polygon(r)
                if p.is_valid and not p.is_empty:
                    all_source_geoms.append(p)
    except Exception:
        pass

# 2. OSM Landuse cache
osm_landuse_f = "data/osm/sweden-urban-osm-landuse.json"
if os.path.exists(osm_landuse_f):
    try:
        d = json.load(open(osm_landuse_f, encoding='utf-8'))
        for r in d.get('core_urban', []):
            if len(r) >= 4:
                p = Polygon(r)
                if p.is_valid and not p.is_empty:
                    all_source_geoms.append(p)
    except Exception:
        pass

# 3. Natural Earth base polygons
ne_f = "data/osm/sweden-urban-raw.json"
if os.path.exists(ne_f):
    try:
        feats = json.load(open(ne_f, encoding='utf-8'))
        for feat in feats:
            geom = shape(feat.get('geometry', {}))
            if geom.is_valid and not geom.is_empty:
                all_source_geoms.append(geom)
    except Exception:
        pass

print(f"Loaded {len(all_source_geoms)} source geometries in {time.time()-t0:.2f}s.")

# Build Spatial Index
tree = STRtree(all_source_geoms)
print(f"Spatial index built in {time.time()-t0:.2f}s.")

final_core = []
final_semi = []

for name, lat, lon, max_km in TOP_25_CITIES:
    lat_km = 111.0
    lon_km = 111.0 * math.cos(math.radians(lat))
    max_d_deg = max_km / lat_km
    center_pt = Point(lon, lat)
    
    # Query spatial index bounding box
    bbox = box(lon - max_d_deg * 1.25, lat - max_d_deg * 1.25, lon + max_d_deg * 1.25, lat + max_d_deg * 1.25)
    candidate_indices = tree.query(bbox)
    
    city_geoms = [all_source_geoms[i] for i in candidate_indices]
    if not city_geoms:
        city_geoms = [center_pt.buffer(max_km / lon_km * 0.5)]

    # 1. Unify all parts
    unified = unary_union(city_geoms)
    
    # 2. 500m Buffer Dissolve: Bridge internal street/wood gaps into one unified, solid mass
    buffered = unified.buffer(0.0050).buffer(-0.0020)
    
    # 3. Clip strictly to the city's max radius circle so it never bridges to other towns
    city_boundary_circle = center_pt.buffer(max_km / lon_km)
    clipped = buffered.intersection(city_boundary_circle)
    
    # 4. Smooth topology
    simplified = clipped.simplify(0.0008, preserve_topology=True)
    if simplified.is_empty:
        continue

    def get_rings(g):
        res = []
        if isinstance(g, Polygon):
            c = list(g.exterior.coords)
            if len(c) >= 4:
                res.append([[round(pt[0], 4), round(pt[1], 4)] for pt in c])
        elif isinstance(g, MultiPolygon):
            for poly in g.geoms:
                if poly.area * (lat_km * lon_km) > 0.08:
                    c = list(poly.exterior.coords)
                    if len(c) >= 4:
                        res.append([[round(pt[0], 4), round(pt[1], 4)] for pt in c])
        return res

    city_rings = get_rings(simplified)
    print(f"  {name}: {len(city_rings)} unified urban polygons.")
    for r in city_rings:
        final_core.append(r)
        cx = sum(p[0] for p in r) / len(r)
        cy = sum(p[1] for p in r) / len(r)
        semi_r = [[round(cx + (p[0] - cx) * 1.25, 4), round(cy + (p[1] - cy) * 1.25, 4)] for p in r]
        final_semi.append(semi_r)

print(f"\nTotal Top 25 unified urban masses: {len(final_core)} (Built in {time.time()-t0:.2f}s).")

# Update sweden-geo.json
geo_path = os.path.join("data", "sweden-geo.json")
with open(geo_path, 'r', encoding='utf-8') as f:
    geo = json.load(f)

geo['core_urban'] = final_core
geo['semi_urban'] = final_semi
geo['city_limits'] = final_core

with open(geo_path, 'w', encoding='utf-8') as f:
    json.dump(geo, f, separators=(',', ':'))

print(f"Updated data/sweden-geo.json successfully! ({os.path.getsize(geo_path)/1024:.1f} KB).")
