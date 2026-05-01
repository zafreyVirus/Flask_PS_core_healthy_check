import os
import glob
import shutil
import zipfile
import pandas as pd
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────

FM_DIR    = "/home/u2020/NBI_FM"
OUT_DIR   = "/home/u2020/NBI_FM"

# 6 output files — overwritten fresh every run
OUTPUT_FILES = {
    "alarm_LMB_vUSN":  os.path.join(OUT_DIR, "alarm_LMB_vUSN.csv"),
    "alarm_CLOUDUSN":  os.path.join(OUT_DIR, "alarm_CLOUDUSN.csv"),
    "alarm_LLG_vCGW":  os.path.join(OUT_DIR, "alarm_LLG_vCGW.csv"),
    "alarm_LLG_vDGW":  os.path.join(OUT_DIR, "alarm_LLG_vDGW.csv"),
    "alarm_LMB_vCGW":  os.path.join(OUT_DIR, "alarm_LMB_vCGW.csv"),
    "alarm_LMB_vDGW":  os.path.join(OUT_DIR, "alarm_LMB_vDGW.csv"),
}

# Filter rules: output_key → (Alarm Source, NEType)
FILTERS = {
    "alarm_LMB_vUSN": ("LMB_vUSN01",  "vUSN"),
    "alarm_CLOUDUSN": ("CLOUDUSN",    "vUSN"),
    "alarm_LLG_vCGW": ("LLG_vCGW01", "vUGW"),
    "alarm_LLG_vDGW": ("LLG_vDGW01", "vUGW"),
    "alarm_LMB_vCGW": ("LMB_vCGW01", "vUGW"),
    "alarm_LMB_vDGW": ("LMB_vDGW01", "vUGW"),
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def read_alarm_csv(filepath):
    """
    Read an alarm CSV file. Handles both:
    - New format: standard CSV with header on row 0
    - Old U2020 format: metadata rows before the real header
    Returns a DataFrame or None on failure.
    """
    try:
        # First try reading directly
        df = pd.read_csv(filepath, on_bad_lines="skip")

        # Check if the real header is in the file but buried
        if "Alarm Source" not in df.columns and "NEType" not in df.columns:
            # Search for the header row
            with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
                lines = f.readlines()

            header_idx = None
            for i, line in enumerate(lines):
                if "Alarm Source" in line or "NEType" in line:
                    header_idx = i
                    break

            if header_idx is None:
                return None

            import io
            content = "".join(lines[header_idx:])
            df = pd.read_csv(io.StringIO(content), on_bad_lines="skip")

        return df

    except Exception as e:
        print(f"[WARN] Could not read {filepath}: {e}")
        return None


def extract_zip(zip_path, extract_to):
    """Unzip a file into a target directory. Returns list of extracted file paths."""
    extracted = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_to)
            extracted = [os.path.join(extract_to, n) for n in z.namelist()]
    except Exception as e:
        print(f"[WARN] Could not unzip {zip_path}: {e}")
    return extracted


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting alarm extraction...")

    # Accumulated data per output key across all folders and files
    accumulated = {key: [] for key in OUTPUT_FILES}

    # Find all dated folders e.g. 20260429, 20260430
    date_folders = sorted([
        f for f in glob.glob(os.path.join(FM_DIR, "*"))
        if os.path.isdir(f) and os.path.basename(f).isdigit()
    ])

    if not date_folders:
        print("[INFO] No dated alarm folders found.")
    else:
        for date_folder in date_folders:
            folder_name = os.path.basename(date_folder)
            print(f"[INFO] Processing {folder_name}...")

            zip_files = glob.glob(os.path.join(date_folder, "*.zip"))

            if not zip_files:
                print(f"  → No zip files found in {folder_name}")
            else:
                # Use a temp dir to extract zips
                tmp_dir = os.path.join(date_folder, "_tmp_extract")
                os.makedirs(tmp_dir, exist_ok=True)

                for zip_path in zip_files:
                    extracted_files = extract_zip(zip_path, tmp_dir)

                    for extracted_file in extracted_files:
                        if not extracted_file.lower().endswith(".csv"):
                            continue

                        df = read_alarm_csv(extracted_file)
                        if df is None or df.empty:
                            continue

                        # Check required columns exist
                        if "Alarm Source" not in df.columns or "NEType" not in df.columns:
                            print(f"  [WARN] Missing Alarm Source/NEType in {os.path.basename(extracted_file)}")
                            continue

                        # Filter for each node
                        for key, (alarm_source, ne_type) in FILTERS.items():
                            mask = (
                                (df["Alarm Source"].astype(str).str.strip() == alarm_source) &
                                (df["NEType"].astype(str).str.strip() == ne_type)
                            )
                            matched = df[mask]
                            if not matched.empty:
                                accumulated[key].append(matched)

                # Clean up temp extraction dir
                shutil.rmtree(tmp_dir, ignore_errors=True)

            # Delete the dated folder after processing
            try:
                shutil.rmtree(date_folder)
                print(f"[INFO] Deleted {date_folder}")
            except Exception as e:
                print(f"[WARN] Could not delete {date_folder}: {e}")

    # Write output files — overwrite fresh every run
    print("\n[INFO] Writing output alarm files...")
    for key, frames in accumulated.items():
        out_path = OUTPUT_FILES[key]

        if frames:
            df_out = pd.concat(frames, ignore_index=True)
            # Remove duplicate rows
            df_out = df_out.drop_duplicates()
            # Sort by OccurrenceTime if available
            if "OccurrenceTime" in df_out.columns:
                df_out = df_out.sort_values("OccurrenceTime")
            df_out.to_csv(out_path, index=False)
            print(f"  → {os.path.basename(out_path)}: {len(df_out)} rows")
        else:
            # Write empty file with no data
            pd.DataFrame().to_csv(out_path, index=False)
            print(f"  → {os.path.basename(out_path)}: no matching alarms")

    print("[INFO] Alarm extraction complete.")


if __name__ == "__main__":
    main()
