# import smtplib
# import os
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.base import MIMEBase
# from email import encoders
# from datetime import datetime

# class EmailReport:

#     def __init__(self, sender_email, sender_password):
#         self.sender_email = sender_email
#         self.sender_password = sender_password

#     def generate_html(self, health_report, start_date, end_date):

#         current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         rows = ""

#         for ne, data in health_report.items():

#             cpu_pct    = data.get("CPU Utilization %")
#             cpu_status = data.get("CPU Health Status", "UNKNOWN")

#             if cpu_status == "HEALTHY":
#                 color = "#28a745"
#             elif cpu_status == "WARNING":
#                 color = "#ffc107"
#             elif cpu_status == "CRITICAL":
#                 color = "#dc3545"
#             else:
#                 color = "#aaaaaa"

#             cpu_display = f"{cpu_pct}%" if cpu_pct is not None else "N/A"

#             rows += f"""
#             <tr>
#                 <td style="padding:8px; border:1px solid #ddd;">{ne}</td>
#                 <td style="padding:8px; border:1px solid #ddd;">{data['Peak Traffic (MB)']:,.2f}</td>
#                 <td style="padding:8px; border:1px solid #ddd;">{data['Peak Time']}</td>
#                 <td style="padding:8px; border:1px solid #ddd; text-align:center;
#                            background-color:{color}; color:white; font-weight:bold;">
#                     {cpu_display}
#                 </td>
#                 <td style="padding:8px; border:1px solid #ddd; color:{color};
#                            font-weight:bold;">{cpu_status}</td>
#             </tr>
#             """

#         html = f"""
#         <html>
#         <body style="font-family: Arial; color: #333;">

#         <div style="text-align:center; background-color:#003366; padding:20px; color:white;">
#             <h2 style="margin:0;">TNM - Core Network</h2>
#             <h3 style="margin:5px 0 0 0;">PS Core Health Report</h3>
#         </div>

#         <div style="padding:20px;">
#             <p><strong>Report Period:</strong> {start_date} to {end_date}</p>
#             <p><strong>Generated On:</strong> {current_time}</p>

#             <h3 style="color:#003366;">Traffic Health Summary</h3>

#             <table border="0" cellpadding="0" cellspacing="0" width="100%"
#                    style="border-collapse:collapse; border:1px solid #ddd;">
#                 <tr style="background-color:#003366; color:white;">
#                     <th style="padding:10px; text-align:left;">NE Name</th>
#                     <th style="padding:10px; text-align:left;">Peak Traffic (MB)</th>
#                     <th style="padding:10px; text-align:left;">Peak Time</th>
#                     <th style="padding:10px; text-align:center;">CPU Utilization %</th>
#                     <th style="padding:10px; text-align:left;">CPU Health Status</th>
#                 </tr>
#                 {rows}
#             </table>

#             <br>
#             <p style="color:#888; font-size:12px;">
#                 The full Excel report with charts and alarm details is attached.
#             </p>
#         </div>

#         </body>
#         </html>
#         """

#         return html

#     def send_report(self, attachment_path, health_report, start_date, end_date):
#         """Send the generated Excel report via email with an HTML summary body."""

#         recipient = os.environ.get("RECIPIENT_EMAIL", "msusafraser@gmail.com")

#         msg = MIMEMultipart("mixed")
#         msg["Subject"] = f"TNM PS Core Health Report — {start_date} to {end_date}"
#         msg["From"]    = self.sender_email
#         msg["To"]      = recipient

#         html_content = self.generate_html(health_report, start_date, end_date)
#         msg.attach(MIMEText(html_content, "html"))

#         with open(attachment_path, "rb") as f:
#             part = MIMEBase("application", "octet-stream")
#             part.set_payload(f.read())

#         encoders.encode_base64(part)
#         part.add_header(
#             "Content-Disposition",
#             "attachment; filename=PS_Core_Health_Report.xlsx"
#         )
#         msg.attach(part)

#         with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
#             server.login(self.sender_email, self.sender_password)
#             server.sendmail(self.sender_email, recipient, msg.as_string())

#         print(f"Email sent successfully to {recipient}")

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime


class EmailReport:

    def __init__(self, sender_email, sender_password):
        self.sender_email = sender_email
        self.sender_password = sender_password

    def _license_color(self, entry):
        days      = entry.get("remain_days")
        permanent = entry.get("permanent", False)
        if permanent:
            return "#000000"
        if days is None:
            return "#888888"
        if days < 14:
            return "#dc3545"
        if days <= 30:
            return "#FF8C00"
        return "#28a745"

    def generate_html(self, health_report, start_date, end_date, license_summary=None):

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ── Traffic / CPU summary rows ────────────────────────────────────────
        # rows = ""
        # for ne, data in health_report.items():
        #     cpu_pct    = data.get("CPU Utilization %")
        #     cpu_status = data.get("CPU Health Status", "UNKNOWN")

        #     if cpu_status == "HEALTHY":
        #         color = "#28a745"
        #     elif cpu_status == "WARNING":
        #         color = "#ffc107"
        #     elif cpu_status == "CRITICAL":
        #         color = "#dc3545"
        #     else:
        #         color = "#aaaaaa"

        #     cpu_display = f"{cpu_pct}%" if cpu_pct is not None else "N/A"

        #     rows += f"""
        #     <tr>
        #         <td style="padding:8px; border:1px solid #ddd;">{ne}</td>
        #         <td style="padding:8px; border:1px solid #ddd;">{data['Peak Traffic (MB)']:,.2f}</td>
        #         <td style="padding:8px; border:1px solid #ddd;">{data['Peak Time']}</td>
        #         <td style="padding:8px; border:1px solid #ddd; text-align:center;
        #                    background-color:{color}; color:white; font-weight:bold;">
        #             {cpu_display}
        #         </td>
        #         <td style="padding:8px; border:1px solid #ddd; color:{color};
        #                    font-weight:bold;">{cpu_status}</td>
        #     </tr>
        #     """

        # ── License summary rows ──────────────────────────────────────────────
        license_rows = ""
        if license_summary:
            for entry in license_summary:
                txt_color = self._license_color(entry)
                license_rows += f"""
                <tr>
                    <td style="padding:8px; border:1px solid #ddd; font-weight:bold;">
                        {entry['node']}
                    </td>
                    <td style="padding:8px; border:1px solid #ddd;
                               color:{txt_color}; font-weight:bold;">
                        {entry['grace_period']}
                    </td>
                </tr>
                """

        # ── HTML body ─────────────────────────────────────────────────────────
        html = f"""
        <html>
        <body style="font-family: Arial; color: #333;">

        <div style="text-align:center; background-color:#003366; padding:20px; color:white;">
            <h2 style="margin:0;">TNM - Core Network</h2>
            <h3 style="margin:5px 0 0 0;">PS Core Health Report</h3>
        </div>

        <div style="padding:20px;">
            <p><strong>Report Period:</strong> {start_date} to {end_date}</p>
            <p><strong>Generated On:</strong> {current_time}</p>


            <h3 style="color:#003366;">License Grace Period Summary</h3>
            <table border="0" cellpadding="0" cellspacing="0" width="60%"
                   style="border-collapse:collapse; border:1px solid #ddd;">
                <tr style="background-color:#003366; color:white;">
                    <th style="padding:10px; text-align:left;">Node</th>
                    <th style="padding:10px; text-align:left;">Grace Period</th>
                </tr>
                {license_rows if license_rows else '<tr><td colspan="2" style="padding:8px; color:#888;">No license data available.</td></tr>'}
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
        """Send the generated Excel report via email with an HTML summary body."""

        recipient = os.environ.get("RECIPIENT_EMAIL", "msusafraser@gmail.com")

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"TNM PS Core Health Report — {start_date} to {end_date}"
        msg["From"]    = self.sender_email
        msg["To"]      = recipient

        html_content = self.generate_html(
            health_report, start_date, end_date, license_summary)
        msg.attach(MIMEText(html_content, "html"))

        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            "attachment; filename=PS_Core_Health_Report.xlsx"
        )
        msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, recipient, msg.as_string())

        print(f"Email sent successfully to {recipient}")