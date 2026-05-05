# import pandas as pd
# import os
# import re

# FM_DIR = "/home/u2020/NBI_FM"

# # Alarm file → friendly node label
# NODE_LICENSE_MAP = [
#     ("alarm_CLOUDUSN.csv", "LLG vUSN"),
#     ("alarm_LMB_vUSN.csv", "LMB vUSN"),
#     ("alarm_LLG_vCGW.csv", "LLG vCGW"),
#     ("alarm_LLG_vDGW.csv", "LLG vDGW"),
#     ("alarm_LMB_vCGW.csv", "LMB vCGW"),
#     ("alarm_LMB_vDGW.csv", "LMB vDGW"),
# ]


# def extract_remain_days(text):
#     """
#     Extract remainDay value from addtional Text string.
#     e.g. 'MO=LcsAlarmInfo, reason=License deadline over, remainDay=32, featureName=Trial0'
#     Returns int or None.
#     """
#     if not text or pd.isna(text):
#         return None
#     match = re.search(r'remainDay=(\d+)', str(text), re.IGNORECASE)
#     if match:
#         return int(match.group(1))
#     return None


# def get_license_summary():
#     """
#     Scan each node's alarm file for license grace period alarms.
#     Returns list of dicts: [{node, remain_days, grace_period_label}]
#     """
#     results = []

#     for filename, node_label in NODE_LICENSE_MAP:
#         filepath = os.path.join(FM_DIR, filename)
#         remain_days = None

#         if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
#             try:
#                 df = pd.read_csv(filepath)

#                 # Look for license alarm rows in addtional Text column
#                 text_col = None
#                 for col in ["addtional Text", "Additional Text", "additionalText"]:
#                     if col in df.columns:
#                         text_col = col
#                         break

#                 if text_col:
#                     # Extract remainDay from each row
#                     df["_remain"] = df[text_col].apply(extract_remain_days)
#                     license_rows = df[df["_remain"].notna()]

#                     if not license_rows.empty:
#                         # Take the minimum (most critical)
#                         remain_days = int(license_rows["_remain"].min())

#             except Exception as e:
#                 print(f"[WARN] Could not read {filename}: {e}")

#         results.append({
#             "node":         node_label,
#             "remain_days":  remain_days,
#             "grace_period": f"{remain_days}-day grace period" if remain_days is not None else "No license alarm",
#         })

#     return results

import pandas as pd
import os
import re

FM_DIR = "/home/u2020/NBI_FM"

# Direct alarm file → friendly node label
DIRECT_NODES = [
    ("alarm_CLOUDUSN.csv", "LLG vUSN"),
    ("alarm_LMB_vUSN.csv", "LMB vUSN"),
    ("alarm_LLG_vCGW.csv", "LLG vCGW"),
    ("alarm_LLG_vDGW.csv", "LLG vDGW"),
    ("alarm_LMB_vCGW.csv", "LMB vCGW"),
    ("alarm_LMB_vDGW.csv", "LMB vDGW"),
]

# Derived nodes — copy grace period from another node
DERIVED_NODES = [
    ("LLG CloudCG", "LLG vDGW"),  # copies LLG vDGW
    ("LMB SPS",     "LMB vCGW"),  # copies LMB vCGW
    ("LLG SPS",     "LLG vCGW"),  # copies LLG vCGW
]

# Fixed permanent nodes
PERMANENT_NODES = ["LMB DCGW"]


def extract_remain_days(text):
    """Extract remainDay=XX from alarm addtional Text. Returns int or None."""
    if not text or pd.isna(text):
        return None
    match = re.search(r'remainDay=(\d+)', str(text), re.IGNORECASE)
    return int(match.group(1)) if match else None


def grace_period_label(remain_days):
    """Format remain_days as a grace period label string."""
    if remain_days is None:
        return "No license alarm"
    return f"{remain_days}-day grace period"


def scan_alarm_file(filepath):
    """
    Scan one alarm CSV for the minimum remainDay value.
    Returns int or None.
    """
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return None
    try:
        df = pd.read_csv(filepath)

        # Find the text column — handle typo in column name
        text_col = None
        for col in ["addtional Text", "Additional Text", "additionalText"]:
            if col in df.columns:
                text_col = col
                break

        if not text_col:
            return None

        df["_remain"] = df[text_col].apply(extract_remain_days)
        license_rows = df[df["_remain"].notna()]

        if license_rows.empty:
            return None

        return int(license_rows["_remain"].min())

    except Exception as e:
        print(f"[WARN] Could not read {filepath}: {e}")
        return None


def get_license_summary():
    """
    Build the full license summary table.
    Returns list of dicts: [{node, remain_days, grace_period}]
    """
    # Step 1 — scan direct nodes
    direct_results = {}
    for filename, node_label in DIRECT_NODES:
        filepath = os.path.join(FM_DIR, filename)
        remain_days = scan_alarm_file(filepath)
        direct_results[node_label] = {
            "node":         node_label,
            "remain_days":  remain_days,
            "grace_period": grace_period_label(remain_days),
        }

    # Step 2 — derived nodes copy from source
    derived_results = {}
    for node_label, source_label in DERIVED_NODES:
        source = direct_results.get(source_label, {})
        remain_days = source.get("remain_days")
        derived_results[node_label] = {
            "node":         node_label,
            "remain_days":  remain_days,
            "grace_period": grace_period_label(remain_days),
        }

    # Step 3 — permanent nodes
    permanent_results = {}
    for node_label in PERMANENT_NODES:
        permanent_results[node_label] = {
            "node":         node_label,
            "remain_days":  None,
            "grace_period": "Permanent",
            "permanent":    True,
        }

    # Step 4 — assemble in display order
    display_order = [
        "LLG vUSN", "LMB vUSN",
        "LLG vCGW", "LLG vDGW",
        "LMB vCGW", "LMB vDGW",
        "LLG CloudCG",
        "LMB SPS", "LLG SPS",
        "LMB DCGW",
    ]

    all_nodes = {**direct_results, **derived_results, **permanent_results}
    return [all_nodes[n] for n in display_order if n in all_nodes]