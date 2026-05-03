# import pandas as pd
# import matplotlib
# matplotlib.use("Agg")
# import matplotlib.pyplot as plt


# class CPUProcessor:
#     """
#     Handles a single node CSV:
#       cloudusn.csv or lmb_vusn.csv
#     Columns: Result Time, Object Name, CPU average usage, CPU max usage, CPU usage
#     """

#     def __init__(self, file_path):
#         self.file_path = file_path
#         self.df = None

#     def load_data(self):
#         self.df = pd.read_csv(self.file_path)
#         self.df["Result Time"] = pd.to_datetime(self.df["Result Time"])

#         # Extract short VM name from Object Name
#         # e.g. "CLOUDUSN/VM:nodeName=VNFP, VM Name=SPU_P_0073" → "SPU_P_0073"
#         self.df["VM Name"] = self.df["Object Name"].str.extract(
#             r"VM Name=(.+)$"
#         )
#         return self.df

#     def plot_cpu_usage(self, output_file, title):
#         """
#         Plot CPU max usage per VM over time.
#         Uses latest 3 days of data automatically.
#         """
#         df = self.df.copy()

#         # Filter to latest 3 days
#         latest = df["Result Time"].max()
#         cutoff = latest - pd.Timedelta(days=3)
#         df = df[df["Result Time"] >= cutoff]

#         pivot = df.pivot_table(
#             index="Result Time",
#             columns="VM Name",
#             values="CPU max usage",
#             aggfunc="mean"
#         )

#         colors = [
#             "red", "brown", "green", "purple", "orange",
#             "black", "blue", "pink", "cyan", "magenta", "olive", "teal"
#         ]

#         plt.figure(figsize=(24, 6))

#         for i, vm in enumerate(pivot.columns):
#             plt.plot(
#                 pivot.index,
#                 pivot[vm],
#                 color=colors[i % len(colors)],
#                 linewidth=2,
#                 marker="o",
#                 markerfacecolor="white",
#                 markeredgewidth=2,
#                 label=vm
#             )

#         plt.title(title)
#         plt.xlabel("Time")
#         plt.ylabel("CPU Max Usage (%)")
#         plt.legend(
#             loc="upper center",
#             bbox_to_anchor=(1.01, 1),
#             borderaxespad=0,
#             fontsize=8
#         )
#         plt.grid(True)
#         plt.xticks(rotation=45)
#         plt.tight_layout(rect=[0, 0, 0.65, 1])
#         plt.savefig(output_file)
#         plt.close()

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch


class CPUProcessor:
    """
    Handles a single node CPU CSV:
      cloudusn.csv or lmb_vusn.csv
    Columns: Result Time, Object Name, CPU average usage, CPU max usage, CPU usage
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        self.df = pd.read_csv(self.file_path)
        self.df["Result Time"] = pd.to_datetime(self.df["Result Time"])

        # Extract short VM name from Object Name
        self.df["VM Name"] = self.df["Object Name"].str.extract(r"VM Name=(.+)$")
        return self.df

    def _resample_hourly(self, df):
        """
        Resample 5-minute data to 60-minute intervals.
        Takes MAX within each hour — shows worst case CPU per hour.
        """
        pivot = df.pivot_table(
            index="Result Time",
            columns="VM Name",
            values="CPU max usage",
            aggfunc="max"
        )
        # Resample to 60 min taking max
        pivot = pivot.resample("60min").max()
        return pivot

    def plot_cpu_usage(self, output_file, title):
        """
        Plot CPU max usage per VM over time at 60-min intervals.
        Shows yellow box with latest max CPU value and VM name.
        """
        df = self.df.copy()

        # Filter to latest 3 days
        latest = df["Result Time"].max()
        cutoff = latest - pd.Timedelta(days=3)
        df = df[df["Result Time"] >= cutoff]

        if df.empty:
            return

        # Resample to hourly
        pivot = self._resample_hourly(df)

        # ── Find latest max CPU ───────────────────────────────────────────────
        latest_row = pivot.iloc[-1]
        latest_time = pivot.index[-1]
        top_vm      = latest_row.idxmax()
        top_cpu     = latest_row.max()

        # ── Plot ──────────────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(24, 7))

        colors = [
            "#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
            "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#ff7f0e",
            "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
            "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5",
        ]

        for i, vm in enumerate(pivot.columns):
            color = colors[i % len(colors)]
            ax.plot(
                pivot.index,
                pivot[vm],
                color=color,
                linewidth=1.8,
                marker="o",
                markersize=4,
                markerfacecolor="white",
                markeredgewidth=1.5,
                label=vm
            )

        # ── Node title top-left (like screenshot) ─────────────────────────────
        ax.text(
            0.01, 0.97, title,
            transform=ax.transAxes,
            fontsize=13, fontweight="bold",
            color="#1565C0",
            verticalalignment="top"
        )

        # ── Yellow box: Maximum CPU ───────────────────────────────────────────
        label_text = f"Maximum CPU : {int(round(top_cpu))}%"
        ax.text(
            0.01, 0.86,
            label_text,
            transform=ax.transAxes,
            fontsize=12, fontweight="bold",
            color="black",
            verticalalignment="top",
            bbox=dict(
                boxstyle="square,pad=0.4",
                facecolor="#FFFF00",
                edgecolor="black",
                linewidth=1.5
            )
        )

        # ── Axes formatting ───────────────────────────────────────────────────
        ax.set_xlabel("Time", fontsize=10)
        ax.set_ylabel("CPU usage (%)", fontsize=10)
        ax.set_ylim(0, 105)
        ax.yaxis.set_major_locator(plt.MultipleLocator(10))
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        ax.tick_params(axis="y", labelsize=9)

        # ── Legend below chart ────────────────────────────────────────────────
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.22),
            ncol=4,
            fontsize=7,
            frameon=True,
            title="VM Name"
        )

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.28)
        plt.savefig(output_file, dpi=120, bbox_inches="tight")
        plt.close()