import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class CUPSProcessor:
    """
    Handles a single node CSV for CGW/DGW nodes:
      llg_vcgw.csv, llg_vdgw.csv, lmb_vcgw.csv, lmb_vdgw.csv
    Columns: Result Time, Object Name, CPU average usage, CPU max usage, CPU usage
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        self.df = pd.read_csv(self.file_path)
        self.df["Result Time"] = pd.to_datetime(self.df["Result Time"])

        # Extract short VM name from Object Name
        self.df["VM Name"] = self.df["Object Name"].str.extract(
            r"VM Name=(.+)$"
        )
        return self.df

    def plot_cpu_usage(self, output_file, title):
        """
        Plot CPU max usage per VM over time.
        Uses latest 3 days of data automatically.
        No node filtering needed — each file is already one node.
        """
        df = self.df.copy()

        # Filter to latest 3 days
        latest = df["Result Time"].max()
        cutoff = latest - pd.Timedelta(days=3)
        df = df[df["Result Time"] >= cutoff]

        pivot = df.pivot_table(
            index="Result Time",
            columns="VM Name",
            values="CPU max usage",
            aggfunc="mean"
        )

        colors = [
            "red", "brown", "green", "purple", "orange",
            "black", "blue", "pink", "cyan", "magenta", "olive", "teal"
        ]

        plt.figure(figsize=(24, 6))

        for i, vm in enumerate(pivot.columns):
            plt.plot(
                pivot.index,
                pivot[vm],
                color=colors[i % len(colors)],
                linewidth=2,
                marker="o",
                markerfacecolor="white",
                markeredgewidth=2,
                label=vm
            )

        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("CPU Max Usage (%)")
        plt.legend(
            loc="upper left",
            bbox_to_anchor=(1.01, 1),
            borderaxespad=0,
            fontsize=8
        )
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout(rect=[0, 0, 0.65, 1])
        plt.savefig(output_file)
        plt.close()