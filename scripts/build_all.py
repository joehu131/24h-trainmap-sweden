import subprocess, sys, time, os

def run_step(script_name, description):
    print(f"\n=======================================================")
    print(f"STEP: {description} ({script_name})")
    print(f"=======================================================")
    t0 = time.time()
    script_path = os.path.join("scripts", script_name)
    ret = subprocess.run([sys.executable, script_path])
    if ret.returncode != 0:
        print(f"ERROR: {script_name} failed with exit code {ret.returncode}")
        sys.exit(ret.returncode)
    print(f"--> {script_name} completed in {time.time() - t0:.2f}s")

if __name__ == "__main__":
    t_start = time.time()
    print("=== STARTING FULL DATA PIPELINE REBUILD ===")
    
    # 1. Generate 7-day timetables and OSM track snapping
    run_step("prepare_osm_data.py", "Extract OSM Tracks & Build 7-Day Timetables")
    
    # 2. Build Top 25 Cohesive Urban Masses
    run_step("build_top25_final.py", "Generate Top 25 Cohesive Urban Footprints")
    
    # 3. Compress Deployment Assets
    run_step("prepare_deploy.py", "Gzip Compress Production Assets (.json.gz)")
    
    print(f"\n=======================================================")
    print(f"SUCCESS: Full pipeline completed in {time.time() - t_start:.2f}s!")
    print(f"=======================================================")
