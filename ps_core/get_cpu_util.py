import pandas as pd
import os

PM_DIR = "/home/u2020/NBI_PM/pm"

# Map traffic NE name → CPU file
NE_CPU_MAP = {
    "LLG_vDGW01": os.path.join(PM_DIR, "llg_vdgw.csv"),
    "LMB_vDGW01": os.path.join(PM_DIR, "lmb_vdgw.csv"),
}


def get_latest_max_cpu(ne_name):
    """
    For a given NE (e.g. LLG_vDGW01), load its CPU CSV,
    find the latest timestamp, and return the highest VM CPU max usage
    at that timestamp. Returns None if data unavailable.
    """
    cpu_file = NE_CPU_MAP.get(ne_name)
    if not cpu_file or not os.path.exists(cpu_file):
        return None

    try:
        df = pd.read_csv(cpu_file)
        df["Result Time"] = pd.to_datetime(df["Result Time"])
        df["CPU max usage"] = pd.to_numeric(df["CPU max usage"], errors="coerce")
        df = df.dropna(subset=["CPU max usage"])

        if df.empty:
            return None

        latest_time = df["Result Time"].max()
        latest_df   = df[df["Result Time"] == latest_time]
        max_cpu     = latest_df["CPU max usage"].max()
        return round(float(max_cpu), 1)

    except Exception as e:
        print(f"[WARN] Could not get CPU for {ne_name}: {e}")
        return None


def cpu_health_status(cpu_pct):
    """Return HEALTHY / WARNING / CRITICAL based on CPU %."""
    if cpu_pct is None:
        return "UNKNOWN"
    if cpu_pct < 70:
        return "HEALTHY"
    elif cpu_pct <= 85:
        return "WARNING"
    else:
        return "CRITICAL"
