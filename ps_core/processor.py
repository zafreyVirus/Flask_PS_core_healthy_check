import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class DataProcessor:

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """
        Load real traffic CSV from /home/u2020/NBI_PM/pm/
        Columns: Start Time, NE Name, User Plane SGi ... in MB
        """
        self.df = pd.read_csv(self.file_path)

        # Convert Start Time to datetime
        self.df["Start Time"] = pd.to_datetime(self.df["Start Time"])

        return self.df

    def filter_by_date(self, start_date, end_date):
        """Filter dataframe to the given date range."""
        mask = (
            (self.df["Start Time"] >= pd.to_datetime(start_date)) &
            (self.df["Start Time"] <= pd.to_datetime(end_date)
             + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
        )
        self.df = self.df.loc[mask]
        return self.df

    def pivot_kpi(self, column_name):
        """Pivot so each NE becomes a column, indexed by Start Time."""
        pivot_df = self.df.pivot_table(
            index="Start Time",
            columns="NE Name",
            values=column_name,
            aggfunc="mean"
        )
        return pivot_df.sort_index()

    def calculate_summary(self, column_name):
        """Calculate max, min, avg and their timestamps per NE."""
        summary = {}

        for node in self.df["NE Name"].unique():
            node_df = self.df[self.df["NE Name"] == node].copy()
            node_df = node_df.dropna(subset=[column_name])

            if node_df.empty:
                continue

            max_idx = node_df[column_name].idxmax()
            min_idx = node_df[column_name].idxmin()

            summary[node] = {
                "max_value": node_df[column_name].max(),
                "max_time":  node_df.loc[max_idx, "Start Time"],
                "min_value": node_df[column_name].min(),
                "min_time":  node_df.loc[min_idx, "Start Time"],
                "avg_value": node_df[column_name].mean(),
            }

        return summary

    def plot_kpi(self, column_name, output_file):
        """Generate KPI line chart per NE and save as image."""
        pivot = self.pivot_kpi(column_name)

        color_map = {
            "LLG_vDGW01": "#007dff",
            "LMB_vDGW01": "#41ba41",
        }

        plt.figure(figsize=(14, 6))

        for ne in pivot.columns:
            color = color_map.get(ne, "#007dff")
            plt.plot(
                pivot.index,
                pivot[ne],
                color=color,
                marker="o",
                linewidth=2,
                markersize=6,
                markerfacecolor="white",
                markeredgecolor=color,
                markeredgewidth=2,
                label=ne,
            )

        plt.title(column_name)
        plt.xlabel("Time")
        plt.ylabel("Traffic (MB)")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_file)
        plt.close()
