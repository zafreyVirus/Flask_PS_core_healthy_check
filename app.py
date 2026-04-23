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

BASE_DIR = os.path.join(os.path.dirname(__file__), "ps_core")

DATA_FILES = {
    "traffic":    os.path.join(BASE_DIR, "PS Data traffic LMB.csv"),
    "cpu_llg":    os.path.join(BASE_DIR, "USN_CPU_LLG.csv"),
    "cpu_lmb":    os.path.join(BASE_DIR, "USN_CPU_LMB.csv"),
    "cups":       os.path.join(BASE_DIR, "ugw.csv"),
    "usn_alarms": os.path.join(BASE_DIR, "USN.csv"),
    "cgw_alarms": os.path.join(BASE_DIR, "cgw.csv"),
    "dgw_alarms": os.path.join(BASE_DIR, "dgw.csv"),
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
    # Traffic
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

    # Traffic charts
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

    # USN CPU charts
    cpu_llg_path = os.path.join(tmp_dir, "cpu_llg.png")
    cpu_lmb_path = os.path.join(tmp_dir, "cpu_lmb.png")

    cpu_llg = CPUProcessor(DATA_FILES["cpu_llg"])
    cpu_llg.load_data()
    cpu_llg.plot_cpu_usage(cpu_llg_path, "LLG USN CPU Usage")

    cpu_lmb = CPUProcessor(DATA_FILES["cpu_lmb"])
    cpu_lmb.load_data()
    cpu_lmb.plot_cpu_usage(cpu_lmb_path, "LMB USN CPU Usage")

    # CUPS CPU charts
    cups_lmb_cgw = os.path.join(tmp_dir, "cups_lmb_cgw.png")
    cups_lmb_dgw = os.path.join(tmp_dir, "cups_lmb_dgw.png")
    cups_llg_cgw = os.path.join(tmp_dir, "cups_llg_cgw.png")
    cups_llg_dgw = os.path.join(tmp_dir, "cups_llg_dgw.png")

    cups = CUPSProcessor(DATA_FILES["cups"])
    cups.load_data()
    cups.plot_node("LMB_vCGW01", cups_lmb_cgw, "LMB CGW CPU Usage")
    cups.plot_node("LMB_vDGW01", cups_lmb_dgw, "LMB DGW CPU Usage")
    cups.plot_node("LLG_vCGW01", cups_llg_cgw, "LLG CGW CPU Usage")
    cups.plot_node("LLG_vDGW01", cups_llg_dgw, "LLG DGW CPU Usage")

    # Alarms
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

    # Build Excel
    excel_path = os.path.join(tmp_dir, "PS_Core_Health_Report.xlsx")
    excel = ExcelReport("Fraser Msusa")
    excel.create_report(
        traffic_charts=[chart_gi, chart_4g, chart_gn, chart_sgi],
        cpu_charts=[cpu_llg_path, cpu_lmb_path],
        health_report=health_report,
        output_file=excel_path,
        cups_charts=[cups_lmb_cgw, cups_lmb_dgw, cups_llg_cgw, cups_llg_dgw],
        usn_alarms=usn_alarms,
        ugw_alarms=ugw_alarms,
    )

    return health_report, start_date, end_date, excel_path


# ─── Shared run function (used by both direct run and Flask route) ─────────────

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


# ─── Flask route (for future automation / server trigger) ─────────────────────

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
    # Run report and send email immediately on startup
    try:
        run_report_and_email()
    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        sys.exit(1)

    # Then start the Flask server (ready for future scheduling/automation)
    print("\n[INFO] Starting Flask server...")
    app.run(debug=False, host="0.0.0.0", port=5000)