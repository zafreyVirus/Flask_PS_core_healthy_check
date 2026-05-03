import os
import glob
import shutil
import zipfile
import pandas as pd
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────

FM_DIR  = "/home/u2020/NBI_FM"
OUT_DIR = "/home/u2020/NBI_FM"

OUTPUT_FILES = {
    "alarm_LMB_vUSN": os.path.join(OUT_DIR, "alarm_LMB_vUSN.csv"),
    "alarm_CLOUDUSN": os.path.join(OUT_DIR, "alarm_CLOUDUSN.csv"),
    "alarm_LLG_vCGW": os.path.join(OUT_DIR, "alarm_LLG_vCGW.csv"),
    "alarm_LLG_vDGW": os.path.join(OUT_DIR, "alarm_LLG_vDGW.csv"),
    "alarm_LMB_vCGW": os.path.join(OUT_DIR, "alarm_LMB_vCGW.csv"),
    "alarm_LMB_vDGW": os.path.join(OUT_DIR, "alarm_LMB_vDGW.csv"),
}

FILTERS = {
    "alarm_LMB_vUSN": ("LMB_vUSN01",  "vUSN"),
    "alarm_CLOUDUSN": ("CLOUDUSN",    "vUSN"),
    "alarm_LLG_vCGW": ("LLG_vCGW01", "vUGW"),
    "alarm_LLG_vDGW": ("LLG_vDGW01", "vUGW"),
    "alarm_LMB_vCGW": ("LMB_vCGW01", "vUGW"),
    "alarm_LMB_vDGW": ("LMB_vDGW01", "vUGW"),
}

# How many days back to keep alarms
DAYS_TO_KEEP = 7

# Unique alarm key columns
KEY_COLS = ["Alarm ID", "Alarm Source"]


# ─── Status helpers ───────────────────────────────────────────────────────────

def is_active(status_value):
    """
    Returns True if the alarm is still active.
    Active = status contains 'unacknowledged' OR 'uncleared' (case-insensitive).
    """
    s = str(status_value).lower().strip()
    return "unacknowledged" in s or "uncleared" in s


def is_cleared(status_value):
    """
    Returns True if the alarm is cleared.
    Cleared = status contains 'cleared' but NOT 'uncleared'.
    """
    s = str(status_value).lower().strip()
    return "cleared" in s and "uncleared" not in s


def make_key(row):
    """Create a unique string key from Alarm ID + Alarm Source."""
    return f"{str(row.get('Alarm ID', '')).strip()}|{str(row.get('Alarm Source', '')).strip()}"



def filter_by_date(df, days=DAYS_TO_KEEP):
    """
    Filter alarm DataFrame to only keep rows where OccurrenceTime
    is within the last `days` days from now.
    Handles format: "2026/1/27 02:00:10 GMT+02:00"
    Rows with unparseable dates are kept (safe default).
    """
    if "OccurrenceTime" not in df.columns:
        return df

    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)

    def parse_time(val):
        try:
            # Strip timezone string e.g. " GMT+02:00" before parsing
            clean = str(val).split(" GMT")[0].strip()
            return pd.to_datetime(clean, format="%Y/%m/%d %H:%M:%S")
        except Exception:
            return None

    parsed = df["OccurrenceTime"].apply(parse_time)
    # Keep rows within window OR rows where date could not be parsed
    mask = parsed.isna() | (parsed >= cutoff)
    filtered = df[mask].copy()
    dropped = len(df) - len(filtered)
    if dropped > 0:
        print(f"    [DATE FILTER] Dropped {dropped} alarm(s) older than {days} days")
    return filtered

# ─── File helpers ─────────────────────────────────────────────────────────────

def read_alarm_csv(filepath):
    """
    Read an alarm CSV. Handles standard format and buried-header format.
    Returns DataFrame or None.
    """
    try:
        df = pd.read_csv(filepath, on_bad_lines="skip")

        if "Alarm Source" not in df.columns or "NEType" not in df.columns:
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


def load_existing(out_path):
    """Load existing alarm CSV into a dict keyed by alarm key."""
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return {}
    try:
        df = pd.read_csv(out_path)
        df = filter_by_date(df)  # drop alarms older than DAYS_TO_KEEP
        if df.empty or "Alarm ID" not in df.columns:
            return {}
        existing = {}
        for _, row in df.iterrows():
            key = make_key(row)
            existing[key] = row.to_dict()
        return existing
    except Exception:
        return {}


def extract_zip(zip_path, extract_to):
    """Unzip into a target directory. Returns list of extracted file paths."""
    extracted = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_to)
            extracted = [os.path.join(extract_to, n) for n in z.namelist()]
    except Exception as e:
        print(f"[WARN] Could not unzip {zip_path}: {e}")
    return extracted


# ─── Core merge logic ─────────────────────────────────────────────────────────

def merge_alarms(existing_dict, new_df):
    """
    Merge new alarm data into existing alarm dict.

    Rules:
    - New alarm (key not in existing) AND active → ADD
    - Existing alarm seen in new data AND still active → UPDATE row
    - Existing alarm seen in new data AND now cleared → REMOVE immediately
    - Existing alarm NOT seen in new data at all → KEEP (still active on system)

    Returns updated dict of active alarms.
    """
    # Build a dict of new alarms keyed by alarm key
    new_dict = {}
    for _, row in new_df.iterrows():
        key = make_key(row)
        if key:
            new_dict[key] = row.to_dict()

    result = dict(existing_dict)  # start from existing

    for key, new_row in new_dict.items():
        status = new_row.get("Status", "")

        if is_cleared(status):
            # Alarm explicitly cleared → remove from active list
            if key in result:
                result.pop(key)
                print(f"    [CLEARED] Removed: {key}")
        elif is_active(status):
            if key not in result:
                # Brand new alarm
                result[key] = new_row
                print(f"    [NEW]     Added:   {key}")
            else:
                # Existing alarm — update with latest data
                result[key] = new_row

    return result


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting alarm extraction...")

    # Find all dated folders e.g. 20260429, 20260430
    date_folders = sorted([
        f for f in glob.glob(os.path.join(FM_DIR, "*"))
        if os.path.isdir(f) and os.path.basename(f).isdigit()
    ])

    if not date_folders:
        print("[INFO] No new alarm folders found — existing alarm files kept untouched.")
        return

    # Accumulate new alarm data per output key from all zips
    new_data = {key: [] for key in OUTPUT_FILES}

    for date_folder in date_folders:
        folder_name = os.path.basename(date_folder)
        print(f"[INFO] Processing {folder_name}...")

        zip_files = glob.glob(os.path.join(date_folder, "*.zip"))

        if not zip_files:
            print(f"  → No zip files in {folder_name}")
        else:
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

                    if "Alarm Source" not in df.columns or "NEType" not in df.columns:
                        print(f"  [WARN] Missing columns in {os.path.basename(extracted_file)}")
                        continue

                    for key, (alarm_source, ne_type) in FILTERS.items():
                        mask = (
                            (df["Alarm Source"].astype(str).str.strip() == alarm_source) &
                            (df["NEType"].astype(str).str.strip() == ne_type)
                        )
                        matched = filter_by_date(df[mask])
                        if not matched.empty:
                            new_data[key].append(matched)

            shutil.rmtree(tmp_dir, ignore_errors=True)

        # Delete dated folder after processing
        try:
            shutil.rmtree(date_folder)
            print(f"[INFO] Deleted {date_folder}")
        except Exception as e:
            print(f"[WARN] Could not delete {date_folder}: {e}")

    # ── Merge new data with existing alarm files ───────────────────────────────
    print("\n[INFO] Merging alarms...")

    for key, frames in new_data.items():
        out_path = OUTPUT_FILES[key]
        label    = os.path.basename(out_path)

        # Load what we currently have on disk
        existing_dict = load_existing(out_path)

        if not frames:
            # No new data for this node — keep existing file untouched
            print(f"  → {label}: no new data — {len(existing_dict)} existing alarm(s) kept")
            continue

        # Combine all new frames for this node
        new_df = pd.concat(frames, ignore_index=True).drop_duplicates()

        # Merge
        updated_dict = merge_alarms(existing_dict, new_df)

        # Write updated active alarms to file
        if updated_dict:
            df_out = pd.DataFrame(list(updated_dict.values()))
            if "OccurrenceTime" in df_out.columns:
                df_out = df_out.sort_values("OccurrenceTime")
            df_out.to_csv(out_path, index=False)
            print(f"  → {label}: {len(df_out)} active alarm(s)")
        else:
            # All alarms cleared — write empty file
            pd.DataFrame().to_csv(out_path, index=False)
            print(f"  → {label}: all alarms cleared")

    print("[INFO] Alarm extraction complete.")


if __name__ == "__main__":
    main()