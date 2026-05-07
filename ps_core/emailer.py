import smtplib
import os
import re
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

FM_DIR = "/home/u2020/NBI_FM"
PM_DIR = "/home/u2020/NBI_PM/pm"

# All alarm files to count severities from
ALARM_FILES = [
    "alarm_CLOUDUSN.csv",
    "alarm_LMB_vUSN.csv",
    "alarm_LLG_vCGW.csv",
    "alarm_LLG_vDGW.csv",
    "alarm_LMB_vCGW.csv",
    "alarm_LMB_vDGW.csv",
]

# CPU files mapped to friendly node names
CPU_FILES = {
    "LLG vUSN":  os.path.join(PM_DIR, "cloudusn.csv"),
    "LMB vUSN":  os.path.join(PM_DIR, "lmb_vusn.csv"),
    "LLG vCGW":  os.path.join(PM_DIR, "llg_vcgw.csv"),
    "LLG vDGW":  os.path.join(PM_DIR, "llg_vdgw.csv"),
    "LMB vCGW":  os.path.join(PM_DIR, "lmb_vcgw.csv"),
    "LMB vDGW":  os.path.join(PM_DIR, "lmb_vdgw.csv"),
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


def format_date_human(date_str):
    """Convert '2026-05-05' to '5th May 2026'."""
    try:
        dt = pd.to_datetime(date_str)
        day = dt.day
        suffix = "th" if 11 <= day <= 13 else {1:"st", 2:"nd", 3:"rd"}.get(day % 10, "th")
        return dt.strftime(f"%-d{suffix} %B %Y")
    except Exception:
        return date_str


def count_alarms():
    """Count total Critical and Major alarms across all node alarm files."""
    critical = 0
    major    = 0

    for filename in ALARM_FILES:
        filepath = os.path.join(FM_DIR, filename)
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            continue
        try:
            df = pd.read_csv(filepath)
            if "Severity" not in df.columns:
                continue
            sev = df["Severity"].astype(str).str.strip().str.lower()
            critical += (sev == "critical").sum()
            major    += (sev == "major").sum()
        except Exception:
            continue

    return int(critical), int(major)


def get_cpu_range():
    """
    For each node get the highest VM CPU at the latest timestamp.
    Then return the lowest and highest from that comparison.
    Returns (low_pct, low_node, high_pct, high_node) or None if no data.
    """
    node_max_cpu = {}

    for node_label, filepath in CPU_FILES.items():
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            continue
        try:
            df = pd.read_csv(filepath)
            df["Result Time"] = pd.to_datetime(df["Result Time"])
            df["CPU max usage"] = pd.to_numeric(df["CPU max usage"], errors="coerce")
            df = df.dropna(subset=["CPU max usage"])
            if df.empty:
                continue
            latest = df["Result Time"].max()
            latest_df = df[df["Result Time"] == latest]
            node_max_cpu[node_label] = float(latest_df["CPU max usage"].max())
        except Exception:
            continue

    if not node_max_cpu:
        return None

    high_node = max(node_max_cpu, key=node_max_cpu.get)
    low_node  = min(node_max_cpu, key=node_max_cpu.get)

    return (
        round(node_max_cpu[low_node],  1),
        low_node,
        round(node_max_cpu[high_node], 1),
        high_node,
    )


def build_license_summary_text(license_summary):
    """Build a readable license highlights sentence."""
    if not license_summary:
        return "No license data available."

    # Group nodes by grace period
    groups = {}
    permanent = []

    for entry in license_summary:
        if entry.get("permanent"):
            permanent.append(entry["node"])
        elif entry["remain_days"] is not None:
            days = entry["remain_days"]
            groups.setdefault(days, []).append(entry["node"])

    parts = []
    for days in sorted(groups.keys()):
        nodes = groups[days]
        node_str = ", ".join(nodes)
        parts.append(f"{node_str} — {days}-day grace period")

    if permanent:
        parts.append(f"{', '.join(permanent)} — Permanent")

    return ". ".join(parts) + "." if parts else "No license alarms found."


def license_color(entry):
    days      = entry.get("remain_days")
    permanent = entry.get("permanent", False)
    if permanent:      return "#000000"
    if days is None:   return "#888888"
    if days < 14:      return "#dc3545"
    if days <= 30:     return "#FF8C00"
    return "#28a745"


# ─── Main email class ─────────────────────────────────────────────────────────

class EmailReport:

    def __init__(self, sender_email, sender_password):
        self.sender_email = sender_email
        self.sender_password = sender_password

    def generate_html(self, health_report, start_date, end_date, license_summary=None):

        greeting     = get_greeting()
        date_human   = format_date_human(end_date)
        critical_cnt, major_cnt = count_alarms()
        cpu_range    = get_cpu_range()
        license_text = build_license_summary_text(license_summary)

        # ── Alarm highlight text ──────────────────────────────────────────────
        if critical_cnt == 0 and major_cnt == 0:
            alarm_text = "No critical or major alarms at this time."
        else:
            parts = []
            if critical_cnt:
                parts.append(f"<strong>{critical_cnt}</strong> critical alarm{'s' if critical_cnt > 1 else ''}")
            if major_cnt:
                parts.append(f"<strong>{major_cnt}</strong> major alarm{'s' if major_cnt > 1 else ''}")
            alarm_text = f"{' and '.join(parts)} across all nodes."

        # ── CPU highlight text ────────────────────────────────────────────────
        def cpu_color(pct):
            if pct < 50:
                return "#28a745"   # green
            elif pct < 70:
                return "#FF8C00"   # orange
            else:
                return "#dc3545"   # red

        if cpu_range:
            low_pct, low_node, high_pct, high_node = cpu_range
            low_color  = cpu_color(low_pct)
            high_color = cpu_color(high_pct)
            cpu_text = (
                f'CPU range from '
                f'<strong style="color:{low_color};">{low_pct}%</strong> <strong>({low_node})</strong> '
                f'to '
                f'<strong style="color:{high_color};">{high_pct}%</strong> <strong>({high_node})</strong>.'
            )
        else:
            cpu_text = "CPU data not available."

        # ── License table rows ────────────────────────────────────────────────
        license_rows = ""
        if license_summary:
            for entry in license_summary:
                color = license_color(entry)
                license_rows += f"""
                <tr>
                    <td style="padding:8px; border:1px solid #ddd; font-weight:bold;">
                        {entry['node']}
                    </td>
                    <td style="padding:8px; border:1px solid #ddd;
                               color:{color}; font-weight:bold;">
                        {entry['grace_period']}
                    </td>
                </tr>
                """

        # ── HTML ──────────────────────────────────────────────────────────────
        html = f"""
        <html>
        <body style="font-family: Arial; color: #333; line-height: 1.6;">

        <div style="text-align:center; background-color:#003366; padding:20px; color:white;">
            <h2 style="margin:0;">TNM - Core Network</h2>
            <h3 style="margin:5px 0 0 0;">PS Core Health Check Report</h3>
        </div>

        <div style="padding:24px;">

            <p>{greeting},</p>

            <p>Please find the attached PS Core Health Check report for today,
               <strong>{date_human}</strong>.</p>

            <p><strong>Here are the Key Highlights:</strong></p>

            <ul style="line-height:2;">
                <li>
                    <strong>KPIs:</strong> All KPIs are within expected range.
                </li>
                <li>
                    <strong>Licenses:</strong> {license_text}
                </li>
                <li>
                    <strong>Alarms:</strong> {alarm_text}
                </li>
                <li>
                    <strong>CPU Usage:</strong> {cpu_text}
                </li>
            </ul>

            <br>
            <h3 style="color:#003366;">License Grace Period Summary</h3>
            <table border="0" cellpadding="0" cellspacing="0" width="60%" align="center"
                   style="border-collapse:collapse; border:1px solid #ddd;">
                <tr style="background-color:#003366; color:white;">
                    <th style="padding:10px; text-align:left;">Node</th>
                    <th style="padding:10px; text-align:left;">Grace Period</th>
                </tr>
                {license_rows if license_rows else
                 '<tr><td colspan="2" style="padding:8px; color:#888;">No license data.</td></tr>'}
            </table>

            <br>
            <p style="color:#888; font-size:12px;">
                The full Excel report with charts and alarm details is attached.
            </p>
        </div>

        </body>
        </html>
        """
        return html

    def send_report(self, attachment_path, health_report, start_date, end_date,
                    license_summary=None):

        # ── Recipients ────────────────────────────────────────────────────────
        to_str  = os.environ.get("TO_RECIPIENTS", "")
        cc_str  = os.environ.get("CC_RECIPIENTS", "")

        to_list  = [e.strip() for e in to_str.split(",")  if e.strip()]
        cc_list  = [e.strip() for e in cc_str.split(",")  if e.strip()]
        all_recipients = to_list + cc_list

        if not all_recipients:
            raise ValueError("No recipients configured. Set TO_RECIPIENTS in .env")

        # ── Build message ─────────────────────────────────────────────────────
        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"TNM PS Core Health Report — {format_date_human(end_date)}"
        msg["From"]    = self.sender_email
        msg["To"]      = ", ".join(to_list)
        if cc_list:
            msg["Cc"]  = ", ".join(cc_list)

        html_content = self.generate_html(
            health_report, start_date, end_date, license_summary)
        msg.attach(MIMEText(html_content, "html"))

        # ── Attach Excel ──────────────────────────────────────────────────────
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            "attachment; filename=PS_Core_Health_Report.xlsx"
        )
        msg.attach(part)

        # ── Send via Office365 SMTP with TLS ──────────────────────────────────
        with smtplib.SMTP("smtp.office365.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, all_recipients, msg.as_string())

        print(f"Email sent to: {', '.join(to_list)}")
        if cc_list:
            print(f"CC: {', '.join(cc_list)}")
