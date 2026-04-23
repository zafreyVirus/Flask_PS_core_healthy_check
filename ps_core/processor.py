import pandas as pd
import matplotlib.pyplot as plt


class DataProcessor:

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """Load Huawei U2020 CSV properly (skip metadata lines)"""

        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        header_line_index = None
        for i, line in enumerate(lines):
            if line.startswith('"Start Time"'):
                header_line_index = i
                break

        if header_line_index is None:
            raise Exception("Could not find data header in CSV file.")

        self.df = pd.read_csv(
            self.file_path,
            skiprows=header_line_index,
            engine='python'
        )

        # Convert Start Time column to datetime
        self.df['Start Time'] = pd.to_datetime(self.df['Start Time'])

        return self.df


    def filter_by_date(self, start_date, end_date):
        """Filter dataframe by selected date range"""

        mask = (
            (self.df['Start Time'] >= pd.to_datetime(start_date)) &
            (self.df['Start Time'] <= pd.to_datetime(end_date))
        )

        self.df = self.df.loc[mask]

        return self.df


    def pivot_kpi(self, column_name):
        """Pivot data so LMB and LLG become columns"""

        pivot_df = self.df.pivot(
            index='Start Time',
            columns='NE Name',
            values=column_name
        )

        pivot_df = pivot_df.sort_index()

        return pivot_df


    def calculate_summary(self, column_name):
        """Calculate max, min, avg and timestamps"""

        summary = {}

        for node in self.df['NE Name'].unique():

            node_df = self.df[self.df['NE Name'] == node]

            max_value = node_df[column_name].max()
            min_value = node_df[column_name].min()
            avg_value = node_df[column_name].mean()

            max_time = node_df.loc[node_df[column_name].idxmax()]['Start Time']
            min_time = node_df.loc[node_df[column_name].idxmin()]['Start Time']

            summary[node] = {
                "max_value": max_value,
                "max_time": max_time,
                "min_value": min_value,
                "min_time": min_time,
                "avg_value": avg_value
            }

        return summary


    def plot_kpi(self, column_name, output_file):
        """
        Generate KPI chart and save as image
        """

        pivot = self.pivot_kpi(column_name)

        plt.figure(figsize=(14, 6))

        # Define node colors
        color_map = {
            "LLG_vDGW01": "#007dff",
            "LMB_vDGW01": "#41ba41"
        }

        for ne in pivot.columns:

            color = color_map.get(ne, "#007dff")

            plt.plot(
                pivot.index,
                pivot[ne],
                color=color,
                marker='o',
                linewidth=2,
                markersize=6,
                markerfacecolor='white',     # white center
                markeredgecolor=color,       # colored border
                markeredgewidth=2,
                label=ne
            )

        plt.title(column_name)
        plt.xlabel("Time")
        plt.ylabel("Traffic")

        plt.legend()

        plt.grid(True)

        plt.xticks(rotation=45)

        plt.tight_layout()

        plt.savefig(output_file)

        plt.close()