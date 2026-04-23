import pandas as pd
import matplotlib.pyplot as plt


class CPUProcessor:

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """
        Load Huawei U2020 CPU CSV properly by skipping metadata
        """

        with open(self.file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        header_line_index = None

        for i, line in enumerate(lines):

            if ("VM Name" in line or "\"VM\"" in line) and "CPU max usage" in line:
                header_line_index = i
                break

        if header_line_index is None:
            raise Exception("Could not find CPU data header in CSV")

        self.df = pd.read_csv(
            self.file_path,
            skiprows=header_line_index,
            engine="python"
        )

        # Normalise column names to what the rest of the code expects
        self.df.rename(columns={
            "Start Time": "Time",
            "VM": "VM Name",
        }, inplace=True)

        # Convert time column
        self.df["Time"] = pd.to_datetime(self.df["Time"])

        return self.df


    def plot_cpu_usage(self, output_file, title):
        """
        Generate CPU line chart per VM
        """

        pivot = self.df.pivot_table(
            index="Time",
            columns="VM Name",
            values="CPU max usage (%)"
        )

        plt.figure(figsize=(24,6))

        # automatic colors
        colors = [
            "red",
            "brown",
            "green",
            "purple",
            "orange",
            "black",
            "blue",
            "pink"
        ]

        for i, vm in enumerate(pivot.columns):

            color = colors[i % len(colors)]

            plt.plot(
                pivot.index,
                pivot[vm],
                color=color,
                linewidth=2,
                marker='o',
                markerfacecolor='white',
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
        plt.subplots_adjust(right=0.65)

        plt.grid(True)

        plt.xticks(rotation=45)

        plt.tight_layout(rect=[0, 0, 0.65, 1])

        plt.savefig(output_file)

        plt.close()