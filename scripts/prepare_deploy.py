import os
import gzip
import json

DATA_DIR = "data"

print("=== Preparing GitHub Pages Deployment Assets (.json.gz) ===")

files_to_compress = [
    "sweden-geo.json",
    "sweden-trains-mon.json",
    "sweden-trains-tue.json",
    "sweden-trains-wed.json",
    "sweden-trains-thu.json",
    "sweden-trains-fri.json",
    "sweden-trains-sat.json",
    "sweden-trains-sun.json"
]

total_orig_mb = 0
total_comp_mb = 0

for fname in files_to_compress:
    in_path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(in_path):
        print(f"Skipping missing file: {in_path}")
        continue
        
    out_path = in_path + ".gz"
    
    orig_sz = os.path.getsize(in_path) / 1024 / 1024
    total_orig_mb += orig_sz
    
    with open(in_path, 'rb') as f_in, gzip.open(out_path, 'wb', compresslevel=9) as f_out:
        f_out.writelines(f_in)
        
    comp_sz = os.path.getsize(out_path) / 1024 / 1024
    total_comp_mb += comp_sz
    
    print(f"  Compressed {fname}: {orig_sz:.1f} MB -> {comp_sz:.1f} MB ({(1 - comp_sz/orig_sz)*100:.1f}% reduction)")

print(f"\nTotal uncompressed size: {total_orig_mb:.1f} MB")
print(f"Total compressed size: {total_comp_mb:.1f} MB")
print(f"Largest single compressed file: {max(os.path.getsize(os.path.join(DATA_DIR, f + '.gz')) for f in files_to_compress if os.path.exists(os.path.join(DATA_DIR, f + '.gz')))/1024/1024:.1f} MB (Well under GitHub's 100 MB limit)")
print("\n=== Deployment Preparation Complete! ===")
