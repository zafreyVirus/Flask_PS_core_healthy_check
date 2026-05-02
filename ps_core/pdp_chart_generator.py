import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

PM_DIR = "/home/u2020/NBI_PM/pm"

# ── KPI counter names in the CSV ──────────────────────────────────────────────
USN_COUNTERS = [
    "S1 mode combined attach success rate",
    "Iu mode MS init PDP context act success rate",
    "Gb mode MS init PDP context act success rate",
    "Iu mode GPRS attach success rate",
    "Gb mode GPRS attach success rate",
]

USN_COLORS = ["purple", "orange", "red", "green", "blue"]

PDP_COUNTER  = "S+PGW create bearer context success ratio"
PDP_COLORS   = {"LLG_vCGW01": "#007dff", "LMB_vCGW01": "#41ba41"}


def _strip_udc(name):
    """Remove {UDC} prefix if present."""
    if name.startswith("{UDC}"):
        return name[5:]
    return name


def plot_usn_kpis(csv_path, output_file, title):
    """
    Plot all 5 USN KPI counters over time from Output_CLOUD.csv
    or Output_LMB.csv. Y-axis 0-100 (%).
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[WARN] Could not read {csv_path}: {e}")
        return False

    df["Result Time"] = pd.to_datetime(df["Result Time"], errors="coerce")
    df = df.dropna(subset=["Result Time"]).sort_values("Result Time")

    # Filter to latest 3 days
    latest  = df["Result Time"].max()
    cutoff  = latest - pd.Timedelta(days=3)
    df      = df[df["Result Time"] >= cutoff]

    if df.empty:
        print(f"[WARN] No data in {csv_path} after date filter.")
        return False

    plt.figure(figsize=(18, 5))

    for counter, color in zip(USN_COUNTERS, USN_COLORS):
        # Strip {UDC} prefix if column has it
        col = next(
            (c for c in df.columns if _strip_udc(c) == counter or c == counter),
            None
        )
        if col is None:
            continue

        series = pd.to_numeric(df[col], errors="coerce")
        plt.plot(
            df["Result Time"], series,
            color=color, linewidth=1.5,
            marker="o", markersize=3,
            markerfacecolor="white", markeredgewidth=1,
            label=counter
        )

    plt.title(title, fontsize=12, fontweight="bold")
    plt.xlabel("Time")
    plt.ylabel("%")
    plt.ylim(0, 105)
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, 1.18),
               ncol=3, fontsize=8, frameon=True)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.xticks(rotation=45, fontsize=8)
    plt.tight_layout()
    plt.savefig(output_file, dpi=120, bbox_inches="tight")
    plt.close()
    return True


def plot_pdp_kpi(csv_path, output_file, title):
    """
    Plot S+PGW create bearer context success ratio for
    LLG_vCGW01 and LMB_vCGW01 on one chart.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[WARN] Could not read {csv_path}: {e}")
        return False

    if PDP_COUNTER not in df.columns:
        print(f"[WARN] Column '{PDP_COUNTER}' not found in {csv_path}")
        return False

    df["Result Time"] = pd.to_datetime(df["Result Time"], errors="coerce")
    df = df.dropna(subset=["Result Time"]).sort_values("Result Time")

    # Filter to latest 3 days
    latest = df["Result Time"].max()
    cutoff = latest - pd.Timedelta(days=3)
    df     = df[df["Result Time"] >= cutoff]

    if df.empty:
        print(f"[WARN] No data in {csv_path} after date filter.")
        return False

    plt.figure(figsize=(18, 5))

    for node, color in PDP_COLORS.items():
        node_df = df[df["Object Name"].str.contains(node, case=False, na=False)]
        if node_df.empty:
            continue

        series = pd.to_numeric(node_df[PDP_COUNTER], errors="coerce")
        plt.plot(
            node_df["Result Time"], series,
            color=color, linewidth=1.5,
            marker="o", markersize=3,
            markerfacecolor="white", markeredgewidth=1,
            label=node
        )

    plt.title(title, fontsize=12, fontweight="bold")
    plt.xlabel("Time")
    plt.ylabel("%")
    plt.ylim(0, 105)
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12),
               ncol=2, fontsize=9, frameon=True)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.xticks(rotation=45, fontsize=8)
    plt.tight_layout()
    plt.savefig(output_file, dpi=120, bbox_inches="tight")
    plt.close()
    return True


def generate_pdp_charts(tmp_dir):
    """
    Generate all 3 Quick PDP KPI charts and return their paths.
    Returns (cloud_chart, lmb_chart, pdp_chart) — None if generation failed.
    """
    cloud_path = os.path.join(tmp_dir, "pdp_cloud.png")
    lmb_path   = os.path.join(tmp_dir, "pdp_lmb.png")
    pdp_path   = os.path.join(tmp_dir, "pdp_4g.png")

    cloud_ok = plot_usn_kpis(
        os.path.join(PM_DIR, "Output_CLOUD.csv"),
        cloud_path,
        "CLOUDUSN — USN KPI Attach & PDP Success Rates (%)"
    )

    lmb_ok = plot_usn_kpis(
        os.path.join(PM_DIR, "Output_LMB.csv"),
        lmb_path,
        "LMB_vUSN01 — USN KPI Attach & PDP Success Rates (%)"
    )

    pdp_ok = plot_pdp_kpi(
        os.path.join(PM_DIR, "4G_PDP.csv"),
        pdp_path,
        "4G PDP — S+PGW Create Bearer Context Success Ratio (%)"
    )

    return (
        cloud_path if cloud_ok else None,
        lmb_path   if lmb_ok   else None,
        pdp_path   if pdp_ok   else None,
    )
