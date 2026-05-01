import pandas as pd
import os

# Columns to use in the Excel report
COLUMNS = [
    "Severity",
    "Alarm ID",
    "AlarmName",
    "NEType",
    "Alarm Source",
    "OccurrenceTime",
    "ClearanceTime",
    "Status",
    "LocationInformation",
    "addtional Text",
]

FM_DIR = "/home/u2020/NBI_FM"

ALARM_FILES = {
    "alarm_LMB_vUSN":  os.path.join(FM_DIR, "alarm_LMB_vUSN.csv"),
    "alarm_CLOUDUSN":  os.path.join(FM_DIR, "alarm_CLOUDUSN.csv"),
    "alarm_LLG_vCGW":  os.path.join(FM_DIR, "alarm_LLG_vCGW.csv"),
    "alarm_LLG_vDGW":  os.path.join(FM_DIR, "alarm_LLG_vDGW.csv"),
    "alarm_LMB_vCGW":  os.path.join(FM_DIR, "alarm_LMB_vCGW.csv"),
    "alarm_LMB_vDGW":  os.path.join(FM_DIR, "alarm_LMB_vDGW.csv"),
}


class AlarmProcessor:

    def __init__(self, file_key):
        """
        file_key: one of the keys in ALARM_FILES
        e.g. 'alarm_LMB_vUSN', 'alarm_CLOUDUSN', etc.
        """
        self.file_key = file_key
        self.file_path = ALARM_FILES[file_key]
        self.df = None

    def load_data(self):
        """Load the extracted alarm CSV for this node."""
        if not os.path.exists(self.file_path):
            print(f"[WARN] Alarm file not found: {self.file_path}")
            self.df = pd.DataFrame(columns=COLUMNS)
            return self.df

        try:
            self.df = pd.read_csv(self.file_path)

            # Keep only columns that exist in this file
            available = [c for c in COLUMNS if c in self.df.columns]
            self.df = self.df[available]

        except Exception as e:
            print(f"[WARN] Could not read {self.file_path}: {e}")
            self.df = pd.DataFrame(columns=COLUMNS)

        return self.df

    def get_alarms(self):
        """Return all alarms for this node."""
        if self.df is None:
            self.load_data()
        return self.df.reset_index(drop=True)
