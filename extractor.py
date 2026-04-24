import os
import glob
import shutil
import pandas as pd
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────

PM_DIR        = "/home/u2020/NBI_PM/pm"
PMNEEXPORT    = "/home/u2020/NBI_PM/pmneexport"

# Output CSV files
OUTPUT_FILES = {
    "llg_vcgw":  os.path.join(PM_DIR, "llg_vcgw.csv"),
    "llg_vdgw":  os.path.join(PM_DIR, "llg_vdgw.csv"),
    "lmb_vusn":  os.path.join(PM_DIR, "lmb_vusn.csv"),
    "lmb_vcgw":  os.path.join(PM_DIR, "lmb_vcgw.csv"),
    "lmb_vdgw":  os.path.join(PM_DIR, "lmb_vdgw.csv"),
    "cloudusn":  os.path.join(PM_DIR, "cloudusn.csv"),
}

# Node name prefix → output key mapping (case-insensitive match on Object Name)
NODE_MAP = {
    "llg_vcgw01": "llg_vcgw",
    "llg_vdgw01": "llg_vdgw",
    "lmb_vusn01": "lmb_vusn",
    "lmb_vcgw01": "lmb_vcgw",
    "lmb_vdgw01": "lmb_vdgw",
    "cloudusn":   "cloudusn",
}

# Columns to keep
KEEP_COLS = [
    "Result Time",
    "Object Name",
    "CPU average usage",
    "CPU max usage",
    "CPU usage",
]

OUTPUT_HEADER = True  # write header only if file doesn't exist yet


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_node_key(object_name):
    """
    Given an Object Name like 'LLG_vCGW01/VM:nodeName=...',
    return the matching output key or None.
    """
    name_lower = str(object_name).lower()
    for prefix, key in NODE_MAP.items():
        if name_lower.startswith(prefix):
            return key
    return None


def ensure_output_files():
    """Create output CSVs with headers if they don't exist yet."""
    for path in OUTPUT_FILES.values():
        if not os.path.exists(path):
            pd.DataFrame(columns=KEEP_COLS).to_csv(path, index=False)
            print(f"[INFO] Created {path}")


def process_csv_file(filepath):
    """
    Read one pmexport CSV, filter for our nodes, return a dict of
    {output_key: DataFrame} with only the columns we want.
    """
    try:
        # Row 1 is the header, row 2 is the units line — skip units row
        df = pd.read_csv(filepath, skiprows=[1], on_bad_lines='skip')
    except Exception as e:
        print(f"[WARN] Could not read {filepath}: {e}")
        return {}

    # Check required columns exist
    required = {"Result Time", "Object Name",
                "CPU average usage", "CPU max usage", "CPU usage"}
    if not required.issubset(set(df.columns)):
        return {}  # not a CPU file, skip silently

    # Drop rows with no Object Name
    df = df.dropna(subset=["Object Name"])

    # Map each row to a node key
    df["_node_key"] = df["Object Name"].apply(get_node_key)

    # Drop rows that don't match any node
    df = df[df["_node_key"].notna()]

    if df.empty:
        return {}

    # Keep only the columns we want + the key
    df = df[KEEP_COLS + ["_node_key"]]

    # Split into per-node DataFrames
    result = {}
    for key, group in df.groupby("_node_key"):
        result[key] = group[KEEP_COLS].copy()

    return result


def append_to_output(data_by_key):
    """Append extracted data to the appropriate output CSV files."""
    for key, df in data_by_key.items():
        if df.empty:
            continue
        out_path = OUTPUT_FILES[key]
        file_exists = os.path.exists(out_path) and os.path.getsize(out_path) > 0
        df.to_csv(out_path, mode="a", header=not file_exists, index=False)


def delete_folder(folder_path):
    """Safely delete a folder and all its contents."""
    try:
        shutil.rmtree(folder_path)
        print(f"[INFO] Deleted {folder_path}")
    except Exception as e:
        print(f"[WARN] Could not delete {folder_path}: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting extraction...")

    ensure_output_files()

    # In-memory set to track folders processed in this run
    processed_this_run = set()

    # Find all pmexport_* folders
    pmexport_folders = sorted(glob.glob(os.path.join(PM_DIR, "pmexport_*")))

    if not pmexport_folders:
        print("[INFO] No pmexport folders found.")
    else:
        for folder in pmexport_folders:
            folder_name = os.path.basename(folder)

            # Skip if already processed in this run
            if folder_name in processed_this_run:
                print(f"[SKIP] {folder_name} already processed this run.")
                continue

            print(f"[INFO] Processing {folder_name}...")

            csv_files = glob.glob(os.path.join(folder, "*.csv"))
            folder_data = {}  # accumulate all data from this folder

            for csv_file in csv_files:
                file_data = process_csv_file(csv_file)
                for key, df in file_data.items():
                    if key in folder_data:
                        folder_data[key] = pd.concat(
                            [folder_data[key], df], ignore_index=True
                        )
                    else:
                        folder_data[key] = df

            # Write accumulated data to output CSVs
            if folder_data:
                append_to_output(folder_data)
                for key, df in folder_data.items():
                    print(f"  → {key}: {len(df)} rows appended")
            else:
                print(f"  → No matching CPU data found in {folder_name}")

            # Mark as processed in memory
            processed_this_run.add(folder_name)

            # Delete the folder now that it's been processed
            delete_folder(folder)

    # Always delete pmneexport if it exists
    if os.path.exists(PMNEEXPORT):
        delete_folder(PMNEEXPORT)
    else:
        print("[INFO] pmneexport folder not found, skipping.")

    print(f"[INFO] Extraction complete. Processed {len(processed_this_run)} folder(s).")


if __name__ == "__main__":
    main()
