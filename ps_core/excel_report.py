from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# Severity colour fills
SEVERITY_FILLS = {
    "Critical": PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid"),
    "Major":    PatternFill(start_color="FF8000", end_color="FF8000", fill_type="solid"),
    "Warning":  PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid"),
    "Minor":    PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid"),
}

HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF")
THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"),  bottom=Side(style="thin")
)

ALARM_COLUMNS = [
    "Severity", "Alarm ID", "AlarmName", "NEType", "Alarm Source",
    "OccurrenceTime", "ClearanceTime", "Status",
    "LocationInformation", "addtional Text",
]

ALARM_COL_WIDTHS = [12, 14, 30, 10, 16, 22, 22, 12, 45, 55]


class ExcelReport:

    def __init__(self, author):
        self.author = author

    def _write_alarm_sheet(self, ws, title, alarms_list):
        """Write a formatted alarm table sheet."""
        ws["A1"] = title
        ws["A1"].font = Font(bold=True, size=14)
        ws["A2"] = f"Author: {self.author}"

        current_row = 4

        for section_title, df in alarms_list:
            ws[f"A{current_row}"] = section_title
            ws[f"A{current_row}"].font = Font(bold=True, size=12, color="1F4E79")
            current_row += 1

            # Header row
            available_cols = [c for c in ALARM_COLUMNS if c in df.columns]
            for col_idx, col_name in enumerate(available_cols, start=1):
                cell = ws.cell(row=current_row, column=col_idx, value=col_name)
                cell.fill = HEADER_FILL
                cell.font = HEADER_FONT
                cell.border = THIN_BORDER
                cell.alignment = Alignment(
                    horizontal="center", vertical="center", wrap_text=True)
            current_row += 1

            # Data rows
            for _, data_row in df.iterrows():
                for col_idx, col_name in enumerate(available_cols, start=1):
                    value = data_row.get(col_name, "")
                    cell = ws.cell(
                        row=current_row, column=col_idx,
                        value=str(value) if value else "")
                    cell.border = THIN_BORDER
                    cell.alignment = Alignment(vertical="center", wrap_text=True)

                    if col_name == "Severity":
                        severity = str(value).strip()
                        if severity in SEVERITY_FILLS:
                            cell.fill = SEVERITY_FILLS[severity]
                            cell.font = Font(bold=True, color="FFFFFF")
                        cell.alignment = Alignment(
                            horizontal="center", vertical="center")
                current_row += 1

            current_row += 2  # gap between sections

        # Column widths
        for col_idx, width in enumerate(ALARM_COL_WIDTHS, start=1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width

    def create_report(
        self, traffic_charts, cpu_charts, health_report, output_file,
        cups_charts=None, usn_alarms=None, ugw_alarms=None,
        pdp_charts=None
    ):
        wb = Workbook()

        # ── SHEET 1: PS Core Traffic ──────────────────────────────────────────
        ws1 = wb.active
        ws1.title = "Weekly PS Core Traffic"
        ws1["A1"] = "PS CORE TRAFFIC REPORT"
        ws1["A2"] = f"Author: {self.author}"

        row = 4
        for chart in traffic_charts:
            img = Image(chart)
            img.width  = 900
            img.height = 300
            ws1.add_image(img, f"A{row}")
            row += 22

        # Health summary table
        row += 2
        headers = ["NE", "Peak Traffic (MB)", "Peak Time",
                   "Min Traffic (MB)", "Min Time",
                   "Average (MB)", "Utilization %", "Health Status"]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws1.cell(row=row, column=col_idx, value=h)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(horizontal="center", vertical="center")
        row += 1

        STATUS_FILLS = {
            "HEALTHY":  PatternFill(start_color="00B050", end_color="00B050", fill_type="solid"),
            "WARNING":  PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid"),
            "CRITICAL": PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid"),
        }

        for ne, stats in health_report.items():
            values = [
                ne,
                stats["Peak Traffic (MB)"],
                str(stats["Peak Time"]),
                stats["Minimum Traffic (MB)"],
                str(stats["Minimum Time"]),
                stats["Average Traffic (MB)"],
                stats["Utilization %"],
                stats["Health Status"],
            ]
            for col_idx, val in enumerate(values, start=1):
                cell = ws1.cell(row=row, column=col_idx, value=val)
                cell.border = THIN_BORDER
                cell.alignment = Alignment(vertical="center")
                if col_idx == 8:  # Health Status column
                    status = str(val).strip().upper()
                    if status in STATUS_FILLS:
                        cell.fill = STATUS_FILLS[status]
                        cell.font = Font(bold=True, color="FFFFFF")
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            row += 1

        # ── SHEET 2: USN CPU ──────────────────────────────────────────────────
        ws2 = wb.create_sheet("USN CPU Usage")
        ws2["A1"] = "USN CPU USAGE REPORT"
        ws2["A2"] = f"Author: {self.author}"

        row = 4
        for chart in cpu_charts:
            img = Image(chart)
            img.width  = 1100
            img.height = 300
            ws2.add_image(img, f"A{row}")
            row += 22

        # ── SHEET 3: CUPS CPU ─────────────────────────────────────────────────
        if cups_charts:
            ws3 = wb.create_sheet("CUPS CPU Usage")
            ws3["A1"] = "CUPS CPU USAGE REPORT"
            ws3["A2"] = f"Author: {self.author}"

            row = 4
            for chart in cups_charts:
                img = Image(chart)
                img.width  = 1100
                img.height = 300
                ws3.add_image(img, f"A{row}")
                row += 22

        # ── SHEET 4: Quick PDP KPIs ───────────────────────────────────────────
        ws_pdp = wb.create_sheet("Quick PDP KPIs")
        ws_pdp["A1"] = "QUICK PDP KPIs REPORT"
        ws_pdp["A1"].font = Font(bold=True, size=14)
        ws_pdp["A2"] = f"Author: {self.author}"

        pdp_row = 4

        pdp_chart_titles = [
            "CLOUDUSN — Attach & PDP Success Rates",
            "LMB_vUSN01 — Attach & PDP Success Rates",
            "4G PDP — S+PGW Bearer Context Success Ratio",
        ]

        if pdp_charts:
            for chart_path, chart_title in zip(pdp_charts, pdp_chart_titles):
                if chart_path is None:
                    continue
                ws_pdp[f"A{pdp_row}"] = chart_title
                ws_pdp[f"A{pdp_row}"].font = Font(bold=True, size=11, color="1F4E79")
                pdp_row += 1

                img = Image(chart_path)
                img.width  = 1100
                img.height = 280
                ws_pdp.add_image(img, f"A{pdp_row}")
                pdp_row += 22
        else:
            ws_pdp["A4"] = "No PDP KPI data available."
            ws_pdp["A4"].font = Font(italic=True, color="888888")

        # ── SHEET 5: USN Alarms ───────────────────────────────────────────────
        if usn_alarms:
            ws4 = wb.create_sheet("USN Alarms")
            self._write_alarm_sheet(ws4, "USN ALARMS REPORT", usn_alarms)

        # ── SHEET 6: UGW Alarms ───────────────────────────────────────────────
        if ugw_alarms:
            ws5 = wb.create_sheet("UGW Alarms")
            self._write_alarm_sheet(ws5, "UGW ALARMS REPORT", ugw_alarms)

        wb.save(output_file)
