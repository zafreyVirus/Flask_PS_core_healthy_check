import matplotlib
matplotlib.use("Agg")

import os
import tempfile
import traceback
from datetime import timedelta
from flask import Flask, jsonify
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ps_core"))

from processor import DataProcessor
from cpu_processor import CPUProcessor
from cups_processor import CUPSProcessor
from alarm_processor import AlarmProcessor
from excel_report import ExcelReport
from emailer import EmailReport

app = Flask(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────

PS_CORE_DIR = os.path.join(os.path.dirname(__file__), "ps_core")
CPU_DIR     = "/home/u2020/NBI_PM/pm"

DATA_FILES = {
    # Traffic & alarms — still in ps_core (dummy for now, real later)
    "traffic":    os.path.join(PS_CORE_DIR, "PS Data traffic LMB.csv"),
    "usn_alarms": os.path.join(PS_CORE_DIR, "USN.csv"),
    "cgw_alarms": os.path.join(PS_CORE_DIR, "cgw.csv"),
    "dgw_alarms": os.path.join(PS_CORE_DIR, "dgw.csv"),

    # Real CPU data from extractor
    "cloudusn":   os.path.join(CPU_DIR, "cloudusn.csv"),
    "lmb_vusn":   os.path.join(CPU_DIR, "lmb_vusn.csv"),
    "llg_vcgw":   os.path.join(CPU_DIR, "llg_vcgw.csv"),
    "llg_vdgw":   os.path.join(CPU_DIR, "llg_vdgw.csv"),
    "lmb_vcgw":   os.path.join(CPU_DIR, "lmb_vcgw.csv"),
    "lmb_vdgw":   os.path.join(CPU_DIR, "lmb_vdgw.csv"),
}

CAPACITY_MB = 20_000_000


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_latest_date_range(processor, days=3):
    latest   = processor.df["Start Time"].max()
    earliest = latest - timedelta(days=days - 1)
    return earliest.strftime("%Y-%m-%d"), latest.strftime("%Y-%m-%d")


def evaluate_health(max_value, capacity):
    utilization = (max_value / capacity) * 100
    if utilization < 70:
        status = "HEALTHY"
    elif utilization <= 85:
        status = "WARNING"
    else:
        status = "CRITICAL"
    return round(utilization, 2), status


# ─── Core report logic ────────────────────────────────────────────────────────

def generate_report(tmp_dir):

    # ── Traffic ───────────────────────────────────────────────────────────────
    processor = DataProcessor(DATA_FILES["traffic"])
    processor.load_data()

    start_date, end_date = get_latest_date_range(processor, days=3)
    print(f"[INFO] Report period: {start_date} to {end_date}")

    processor.filter_by_date(start_date, end_date)
    summary = processor.calculate_summary("4G Data traffic VDGW(CLOUD) (MB)")

    health_report = {}
    for ne, stats in summary.items():
        utilization, status = evaluate_health(stats["max_value"], CAPACITY_MB)
        health_report[ne] = {
            "Peak Traffic (MB)":    float(stats["max_value"]),
            "Peak Time":            str(stats["max_time"]),
            "Minimum Traffic (MB)": float(stats["min_value"]),
            "Minimum Time":         str(stats["min_time"]),
            "Average Traffic (MB)": round(float(stats["avg_value"]), 2),
            "Utilization %":        utilization,
            "Health Status":        status,
        }

    # ── Traffic charts ────────────────────────────────────────────────────────
    chart_gi  = os.path.join(tmp_dir, "chart_gi.png")
    chart_4g  = os.path.join(tmp_dir, "chart_4g.png")
    chart_gn  = os.path.join(tmp_dir, "chart_gn.png")
    chart_sgi = os.path.join(tmp_dir, "chart_sgi.png")

    processor.plot_kpi("PGW-U 2/3G Gi traffic in MB (MB)", chart_gi)
    processor.plot_kpi("4G Data traffic VDGW(CLOUD) (MB)", chart_4g)
    processor.plot_kpi("PGW-U 2/3G Gn peak throughput in MB/s (MB/s)", chart_gn)
    processor.plot_kpi(
        "User Plane SGi downlink user traffic peak throughput in MB/s (MB/s) (MB/s)",
        chart_sgi
    )

    # ── USN CPU charts (real data) ────────────────────────────────────────────
    cpu_cloudusn_path = os.path.join(tmp_dir, "cpu_cloudusn.png")
    cpu_lmb_vusn_path = os.path.join(tmp_dir, "cpu_lmb_vusn.png")

    cpu_cloudusn = CPUProcessor(DATA_FILES["cloudusn"])
    cpu_cloudusn.load_data()
    cpu_cloudusn.plot_cpu_usage(cpu_cloudusn_path, "CLOUDUSN CPU Usage")

    cpu_lmb_vusn = CPUProcessor(DATA_FILES["lmb_vusn"])
    cpu_lmb_vusn.load_data()
    cpu_lmb_vusn.plot_cpu_usage(cpu_lmb_vusn_path, "LMB vUSN01 CPU Usage")

    # ── CUPS CPU charts (real data) ───────────────────────────────────────────
    cups_llg_vcgw_path = os.path.join(tmp_dir, "cups_llg_vcgw.png")
    cups_llg_vdgw_path = os.path.join(tmp_dir, "cups_llg_vdgw.png")
    cups_lmb_vcgw_path = os.path.join(tmp_dir, "cups_lmb_vcgw.png")
    cups_lmb_vdgw_path = os.path.join(tmp_dir, "cups_lmb_vdgw.png")

    cups_llg_vcgw = CUPSProcessor(DATA_FILES["llg_vcgw"])
    cups_llg_vcgw.load_data()
    cups_llg_vcgw.plot_cpu_usage(cups_llg_vcgw_path, "LLG vCGW01 CPU Usage")

    cups_llg_vdgw = CUPSProcessor(DATA_FILES["llg_vdgw"])
    cups_llg_vdgw.load_data()
    cups_llg_vdgw.plot_cpu_usage(cups_llg_vdgw_path, "LLG vDGW01 CPU Usage")

    cups_lmb_vcgw = CUPSProcessor(DATA_FILES["lmb_vcgw"])
    cups_lmb_vcgw.load_data()
    cups_lmb_vcgw.plot_cpu_usage(cups_lmb_vcgw_path, "LMB vCGW01 CPU Usage")

    cups_lmb_vdgw = CUPSProcessor(DATA_FILES["lmb_vdgw"])
    cups_lmb_vdgw.load_data()
    cups_lmb_vdgw.plot_cpu_usage(cups_lmb_vdgw_path, "LMB vDGW01 CPU Usage")

    # ── Alarms ────────────────────────────────────────────────────────────────
    alarms = AlarmProcessor(DATA_FILES["usn_alarms"])
    alarms.load_data()
    usn_alarms = [
        ("LLG USN Alarms (CLOUDUSN)",   alarms.get_llg_alarms()),
        ("LMB USN Alarms (LMB_vUSN01)", alarms.get_lmb_alarms()),
    ]

    cgw_alarms = AlarmProcessor(DATA_FILES["cgw_alarms"])
    cgw_alarms.load_data()

    dgw_alarms = AlarmProcessor(DATA_FILES["dgw_alarms"])
    dgw_alarms.load_data()

    ugw_alarms = [
        ("LLG CGW Alarms (LLG_vCGW01)", cgw_alarms.get_by_source("LLG_vCGW01")),
        ("LMB CGW Alarms (LMB_vCGW01)", cgw_alarms.get_by_source("LMB_vCGW01")),
        ("LLG DGW Alarms (LLG_vDGW01)", dgw_alarms.get_by_source("LLG_vDGW01")),
        ("LMB DGW Alarms (LMB_vDGW01)", dgw_alarms.get_by_source("LMB_vDGW01")),
    ]

    # ── Build Excel ───────────────────────────────────────────────────────────
    excel_path = os.path.join(tmp_dir, "PS_Core_Health_Report.xlsx")
    excel = ExcelReport("Fraser Msusa")
    excel.create_report(
        traffic_charts=[chart_gi, chart_4g, chart_gn, chart_sgi],
        cpu_charts=[cpu_cloudusn_path, cpu_lmb_vusn_path],
        health_report=health_report,
        output_file=excel_path,
        cups_charts=[
            cups_llg_vcgw_path, cups_llg_vdgw_path,
            cups_lmb_vcgw_path, cups_lmb_vdgw_path
        ],
        usn_alarms=usn_alarms,
        ugw_alarms=ugw_alarms,
    )

    return health_report, start_date, end_date, excel_path


# ─── Shared run function ──────────────────────────────────────────────────────

def run_report_and_email():
    sender_email    = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")

    if not sender_email or not sender_password:
        raise ValueError("SENDER_EMAIL or SENDER_PASSWORD not set in .env file.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        print("[INFO] Generating report...")
        health_report, start_date, end_date, excel_path = generate_report(tmp_dir)

        print("[INFO] Sending email...")
        emailer = EmailReport(sender_email, sender_password)
        emailer.send_report(excel_path, health_report, start_date, end_date)

    print("[INFO] Done. Temp files cleaned up.")
    return start_date, end_date


# ─── Flask routes ─────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "PS Core Health Report",
        "endpoints": {
            "GET /generate-report": "Generate report and send via email"
        }
    })


@app.route("/generate-report", methods=["GET"])
def generate_report_endpoint():
    try:
        start_date, end_date = run_report_and_email()
        return jsonify({
            "status":  "success",
            "message": "Report generated and emailed successfully.",
            "period":  f"{start_date} to {end_date}",
            "sent_to": os.environ.get("RECIPIENT_EMAIL", "msusafraser@gmail.com"),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        run_report_and_email()
    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n[INFO] Starting Flask server...")
    app.run(debug=False, host="0.0.0.0", port=5000)