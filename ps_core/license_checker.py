import pandas as pd
import os
import re

FM_DIR = "/home/u2020/NBI_FM"

# Alarm file → friendly node label
NODE_LICENSE_MAP = [
    ("alarm_CLOUDUSN.csv", "LLG vUSN"),
    ("alarm_LMB_vUSN.csv", "LMB vUSN"),
    ("alarm_LLG_vCGW.csv", "LLG vCGW"),
    ("alarm_LLG_vDGW.csv", "LLG vDGW"),
    ("alarm_LMB_vCGW.csv", "LMB vCGW"),
    ("alarm_LMB_vDGW.csv", "LMB vDGW"),
]


def extract_remain_days(text):
    """
    Extract remainDay value from addtional Text string.
    e.g. 'MO=LcsAlarmInfo, reason=License deadline over, remainDay=32, featureName=Trial0'
    Returns int or None.
    """
    if not text or pd.isna(text):
        return None
    match = re.search(r'remainDay=(\d+)', str(text), re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def get_license_summary():
    """
    Scan each node's alarm file for license grace period alarms.
    Returns list of dicts: [{node, remain_days, grace_period_label}]
    """
    results = []

    for filename, node_label in NODE_LICENSE_MAP:
        filepath = os.path.join(FM_DIR, filename)
        remain_days = None

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            try:
                df = pd.read_csv(filepath)

                # Look for license alarm rows in addtional Text column
                text_col = None
                for col in ["addtional Text", "Additional Text", "additionalText"]:
                    if col in df.columns:
                        text_col = col
                        break

                if text_col:
                    # Extract remainDay from each row
                    df["_remain"] = df[text_col].apply(extract_remain_days)
                    license_rows = df[df["_remain"].notna()]

                    if not license_rows.empty:
                        # Take the minimum (most critical)
                        remain_days = int(license_rows["_remain"].min())

            except Exception as e:
                print(f"[WARN] Could not read {filename}: {e}")

        results.append({
            "node":         node_label,
            "remain_days":  remain_days,
            "grace_period": f"{remain_days}-day grace period" if remain_days is not None else "No license alarm",
        })

    return results
