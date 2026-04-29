import os
import glob
import shutil
import pandas as pd
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────

PM_DIR     = "/home/u2020/NBI_PM/pm"
PMNEEXPORT = "/home/u2020/NBI_PM/pmneexport"

# ── CPU output files ──────────────────────────────────────────────────────────
CPU_OUTPUT_FILES = {
    "llg_vcgw": os.path.join(PM_DIR, "llg_vcgw.csv"),
    "llg_vdgw": os.path.join(PM_DIR, "llg_vdgw.csv"),
    "lmb_vusn": os.path.join(PM_DIR, "lmb_vusn.csv"),
    "lmb_vcgw": os.path.join(PM_DIR, "lmb_vcgw.csv"),
    "lmb_vdgw": os.path.join(PM_DIR, "lmb_vdgw.csv"),
    "cloudusn": os.path.join(PM_DIR, "cloudusn.csv"),
}

CPU_NODE_MAP = {
    "llg_vcgw01": "llg_vcgw",
    "llg_vdgw01": "llg_vdgw",
    "lmb_vusn01": "lmb_vusn",
    "lmb_vcgw01": "lmb_vcgw",
    "lmb_vdgw01": "lmb_vdgw",
    "cloudusn":   "cloudusn",
}

CPU_KEEP_COLS = [
    "Result Time",
    "Object Name",
    "CPU average usage",
    "CPU max usage",
    "CPU usage",
]

# ── Traffic output files ───────────────────────────────────────────────────────
TRAFFIC_OUTPUT_FILES = {
    "ps_data_traffic":     os.path.join(PM_DIR, "PS Data traffic.csv"),
    "ps_data_traffic_lmb": os.path.join(PM_DIR, "PS Data traffic LMB.csv"),
}

TRAFFIC_NODE_MAP = {
    "llg_vdgw01": "ps_data_traffic",
    "lmb_vdgw01": "ps_data_traffic_lmb",
}

# Columns to extract from traffic files (KB → MB conversion applied)
TRAFFIC_SOURCE_COLS = [
    "User Plane SGi downlink user traffic in KB",
    "User Plane SGi downlink user traffic peak throughput in KB/s",
    "User Plane SGi uplink user traffic in KB",
    "User Plane SGi uplink user traffic peak throughput in KB/s",
]

# Final column names after KB→MB conversion
TRAFFIC_KEEP_COLS = [
    "Start Time",
    "NE Name",
    "User Plane SGi downlink user traffic in MB",
    "User Plane SGi downlink user traffic peak throughput in MB/s",
    "User Plane SGi uplink user traffic in MB",
    "User Plane SGi uplink user traffic peak throughput in MB/s",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_cpu_node_key(object_name):
    name_lower = str(object_name).lower()
    for prefix, key in CPU_NODE_MAP.items():
        if name_lower.startswith(prefix):
            return key
    return None


def get_traffic_node_key(object_name):
    name_lower = str(object_name).lower()
    for prefix, key in TRAFFIC_NODE_MAP.items():
        if name_lower.startswith(prefix):
            return key
    return None


def get_ne_name(object_name):
    """Extract node name prefix e.g. LLG_vDGW01 from full Object Name."""
    return str(object_name).split("/")[0]


def ensure_output_files():
    """Create all output CSVs with headers if they don't exist yet."""
    for path in CPU_OUTPUT_FILES.values():
        if not os.path.exists(path):
            pd.DataFrame(columns=CPU_KEEP_COLS).to_csv(path, index=False)
            print(f"[INFO] Created {path}")

    for path in TRAFFIC_OUTPUT_FILES.values():
        if not os.path.exists(path):
            pd.DataFrame(columns=TRAFFIC_KEEP_COLS).to_csv(path, index=False)
            print(f"[INFO] Created {path}")


def process_cpu_file(filepath):
    """
    Detect and process a CPU file.
    Returns {output_key: DataFrame} or {} if not a CPU file.
    """
    try:
        df = pd.read_csv(filepath, skiprows=[1], on_bad_lines="skip")
    except Exception as e:
        print(f"[WARN] Could not read {filepath}: {e}")
        return {}

    required = {"Result Time", "Object Name",
                "CPU average usage", "CPU max usage", "CPU usage"}
    if not required.issubset(set(df.columns)):
        return {}

    df = df.dropna(subset=["Object Name"])
    df["_node_key"] = df["Object Name"].apply(get_cpu_node_key)
    df = df[df["_node_key"].notna()]

    if df.empty:
        return {}

    result = {}
    for key, group in df.groupby("_node_key"):
        result[key] = group[CPU_KEEP_COLS].copy()

    return result


def process_traffic_file(filepath):
    """
    Detect and process a traffic file.
    Returns {output_key: DataFrame} or {} if not a traffic file.
    Converts KB → MB, renames Result Time → Start Time,
    extracts NE Name from Object Name.
    """
    try:
        # Read header only first to check if this is a traffic file
        header_df = pd.read_csv(filepath, nrows=0)
        if "User Plane SGi downlink user traffic in KB" not in header_df.columns:
            return {}

        # It's a traffic file — read properly, skipping the units row (row index 1)
        df = pd.read_csv(filepath, skiprows=[1], on_bad_lines="skip")
    except Exception as e:
        print(f"[WARN] Could not read {filepath}: {e}")
        return {}

    # Confirm all needed source columns exist
    if not all(col in df.columns for col in TRAFFIC_SOURCE_COLS):
        return {}

    df = df.dropna(subset=["Object Name"])

    # Determine node key
    df["_node_key"] = df["Object Name"].apply(get_traffic_node_key)
    df = df[df["_node_key"].notna()]

    if df.empty:
        return {}

    # Extract NE Name from Object Name
    df["NE Name"] = df["Object Name"].apply(get_ne_name)

    # Rename Result Time → Start Time
    df = df.rename(columns={"Result Time": "Start Time"})

    # Convert KB → MB (divide by 1024)
    df["User Plane SGi downlink user traffic in MB"] = (
        pd.to_numeric(df["User Plane SGi downlink user traffic in KB"],
                      errors="coerce") / 1024
    ).round(4)

    df["User Plane SGi downlink user traffic peak throughput in MB/s"] = (
        pd.to_numeric(
            df["User Plane SGi downlink user traffic peak throughput in KB/s"],
            errors="coerce") / 1024
    ).round(4)

    df["User Plane SGi uplink user traffic in MB"] = (
        pd.to_numeric(df["User Plane SGi uplink user traffic in KB"],
                      errors="coerce") / 1024
    ).round(4)

    df["User Plane SGi uplink user traffic peak throughput in MB/s"] = (
        pd.to_numeric(
            df["User Plane SGi uplink user traffic peak throughput in KB/s"],
            errors="coerce") / 1024
    ).round(4)

    result = {}
    for key, group in df.groupby("_node_key"):
        result[key] = group[TRAFFIC_KEEP_COLS].copy()

    return result


def append_to_output(data_by_key, output_files):
    """Append extracted data to the appropriate output CSV files."""
    for key, df in data_by_key.items():
        if df.empty:
            continue
        out_path = output_files[key]
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

    processed_this_run = set()

    pmexport_folders = sorted(glob.glob(os.path.join(PM_DIR, "pmexport_*")))

    if not pmexport_folders:
        print("[INFO] No pmexport folders found.")
    else:
        for folder in pmexport_folders:
            folder_name = os.path.basename(folder)

            if folder_name in processed_this_run:
                print(f"[SKIP] {folder_name} already processed this run.")
                continue

            print(f"[INFO] Processing {folder_name}...")

            csv_files = glob.glob(os.path.join(folder, "*.csv"))

            cpu_folder_data     = {}
            traffic_folder_data = {}

            for csv_file in csv_files:

                # Try CPU extraction
                cpu_data = process_cpu_file(csv_file)
                for key, df in cpu_data.items():
                    if key in cpu_folder_data:
                        cpu_folder_data[key] = pd.concat(
                            [cpu_folder_data[key], df], ignore_index=True)
                    else:
                        cpu_folder_data[key] = df

                # Try traffic extraction
                traffic_data = process_traffic_file(csv_file)
                for key, df in traffic_data.items():
                    if key in traffic_folder_data:
                        traffic_folder_data[key] = pd.concat(
                            [traffic_folder_data[key], df], ignore_index=True)
                    else:
                        traffic_folder_data[key] = df

            # Write CPU data
            if cpu_folder_data:
                append_to_output(cpu_folder_data, CPU_OUTPUT_FILES)
                for key, df in cpu_folder_data.items():
                    print(f"  → CPU  {key}: {len(df)} rows appended")
            else:
                print(f"  → No CPU data found in {folder_name}")

            # Write traffic data
            if traffic_folder_data:
                append_to_output(traffic_folder_data, TRAFFIC_OUTPUT_FILES)
                for key, df in traffic_folder_data.items():
                    print(f"  → Traffic {key}: {len(df)} rows appended")
            else:
                print(f"  → No traffic data found in {folder_name}")

            processed_this_run.add(folder_name)
            delete_folder(folder)

    # Always delete pmneexport if it exists
    if os.path.exists(PMNEEXPORT):
        delete_folder(PMNEEXPORT)
    else:
        print("[INFO] pmneexport folder not found, skipping.")

    print(f"[INFO] Extraction complete. Processed {len(processed_this_run)} folder(s).")


if __name__ == "__main__":
    main()
