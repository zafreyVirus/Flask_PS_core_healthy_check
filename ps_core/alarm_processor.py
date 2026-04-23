import pandas as pd
import io


COLUMNS = [
    "Severity",
    "Alarm ID",
    "Name",
    "NE Type",
    "Alarm Source",
    "MO Name",
    "Location Information",
    "First Occurred (NT)",
    "Additional Information"
]


class AlarmProcessor:

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """
        Load Huawei U2020 alarm CSV by skipping metadata rows
        """

        with open(self.file_path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()

        header_line_index = None

        for i, line in enumerate(lines):
            if "Severity" in line and "Alarm ID" in line:
                header_line_index = i
                break

        if header_line_index is None:
            raise Exception("Could not find alarm data header in CSV")

        content = "".join(lines[header_line_index:])
        self.df = pd.read_csv(io.StringIO(content))

        # Clean up tab junk values to empty string
        self.df.replace(r"^\s*-\s*$", "", regex=True, inplace=True)

        return self.df

    def get_llg_alarms(self):
        """
        Return alarms for LLG USN (Alarm Source = CLOUDUSN)
        """
        return self.df[self.df["Alarm Source"] == "CLOUDUSN"][COLUMNS].reset_index(drop=True)

    def get_lmb_alarms(self):
        """
        Return alarms for LMB USN (Alarm Source = LMB_vUSN01)
        """
        return self.df[self.df["Alarm Source"] == "LMB_vUSN01"][COLUMNS].reset_index(drop=True)

    def get_by_source(self, alarm_source):
        """
        Return alarms filtered by any Alarm Source value
        """
        return self.df[self.df["Alarm Source"] == alarm_source][COLUMNS].reset_index(drop=True)