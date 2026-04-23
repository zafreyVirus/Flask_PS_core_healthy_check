import pandas as pd
import matplotlib.pyplot as plt


class CUPSProcessor:

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """
        Load Huawei U2020 CUPS CPU CSV by skipping metadata header rows
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

        # Normalise column names
        self.df.rename(columns={
            "Start Time": "Time",
            "VM": "VM Name",
        }, inplace=True)

        # Convert time column
        self.df["Time"] = pd.to_datetime(self.df["Time"])

        return self.df

    def plot_node(self, ne_name, output_file, title):
        """
        Filter by NE Name and generate a CPU line chart per VM
        """

        node_df = self.df[self.df["NE Name"] == ne_name].copy()

        if node_df.empty:
            raise Exception(f"No data found for NE Name: {ne_name}")

        pivot = node_df.pivot_table(
            index="Time",
            columns="VM Name",
            values="CPU max usage (%)"
        )

        plt.figure(figsize=(24, 6))

        colors = [
            "red",
            "brown",
            "green",
            "purple",
            "orange",
            "black",
            "blue",
            "pink",
            "cyan",
            "magenta",
            "olive",
            "teal"
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