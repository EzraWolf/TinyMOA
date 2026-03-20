import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def analyze_dc_profiling(file_path):
    CURRENT_DIR = os.getcwd()
    file_path = os.path.join(CURRENT_DIR, file_path)

    # Read the 8 voltage levels (Level 0 through 7)
    cols = [
        "index",
        "lvl_0",
        "lvl_1",
        "lvl_2",
        "lvl_3",
        "lvl_4",
        "lvl_5",
        "lvl_6",
        "lvl_7",
    ]
    data = pd.read_csv(file_path, sep=r"\s+", header=None, names=cols)
    # 1.2V range / 7 steps = ~171.4mV ideal spacing
    lsb_step_mv = 1200 / (2**3 - 1)

    # Manually get mean and stdev for each column
    lvl_0_mean = data["lvl_0"].mean()
    lvl_1_mean = data["lvl_1"].mean()
    lvl_2_mean = data["lvl_2"].mean()
    lvl_3_mean = data["lvl_3"].mean()
    lvl_4_mean = data["lvl_4"].mean()
    lvl_5_mean = data["lvl_5"].mean()
    lvl_6_mean = data["lvl_6"].mean()
    lvl_7_mean = data["lvl_7"].mean()

    lvl_0_std = data["lvl_0"].std()
    lvl_1_std = data["lvl_1"].std()
    lvl_2_std = data["lvl_2"].std()
    lvl_3_std = data["lvl_3"].std()
    lvl_4_std = data["lvl_4"].std()
    lvl_5_std = data["lvl_5"].std()
    lvl_6_std = data["lvl_6"].std()
    lvl_7_std = data["lvl_7"].std()

    print("Monte Carlo Results for DC Write Profiling:")
    print(f"Ideal Step Size:   {lsb_step_mv:.2f}mV")
    print(
        f"Level 0 Mean: {lvl_0_mean:.4f}V | Base Level | 3-Sigma: {3 * lvl_0_std * 1000:.2f}mV"
    )
    print(
        f"Level 1 Mean: {lvl_1_mean:.4f}V | Step from L0: {(lvl_1_mean - lvl_0_mean) * 1000:.2f}mV | 3-Sigma: {3 * lvl_1_std * 1000:.2f}mV"
    )
    print(
        f"Level 2 Mean: {lvl_2_mean:.4f}V | Step from L1: {(lvl_2_mean - lvl_1_mean) * 1000:.2f}mV | 3-Sigma: {3 * lvl_2_std * 1000:.2f}mV"
    )
    print(
        f"Level 3 Mean: {lvl_3_mean:.4f}V | Step from L2: {(lvl_3_mean - lvl_2_mean) * 1000:.2f}mV | 3-Sigma: {3 * lvl_3_std * 1000:.2f}mV"
    )
    print(
        f"Level 4 Mean: {lvl_4_mean:.4f}V | Step from L3: {(lvl_4_mean - lvl_3_mean) * 1000:.2f}mV | 3-Sigma: {3 * lvl_4_std * 1000:.2f}mV"
    )
    print(
        f"Level 5 Mean: {lvl_5_mean:.4f}V | Step from L4: {(lvl_5_mean - lvl_4_mean) * 1000:.2f}mV | 3-Sigma: {3 * lvl_5_std * 1000:.2f}mV"
    )
    print(
        f"Level 6 Mean: {lvl_6_mean:.4f}V | Step from L5: {(lvl_6_mean - lvl_5_mean) * 1000:.2f}mV | 3-Sigma: {3 * lvl_6_std * 1000:.2f}mV"
    )
    print(
        f"Level 7 Mean: {lvl_7_mean:.4f}V | Step from L6: {(lvl_7_mean - lvl_6_mean) * 1000:.2f}mV | 3-Sigma: {3 * lvl_7_std * 1000:.2f}mV"
    )
    print("-" * 40)
    avg_measured_step = np.mean(
        [
            (lvl_1_mean - lvl_0_mean) * 1000,
            (lvl_2_mean - lvl_1_mean) * 1000,
            (lvl_3_mean - lvl_2_mean) * 1000,
            (lvl_4_mean - lvl_3_mean) * 1000,
            (lvl_5_mean - lvl_4_mean) * 1000,
            (lvl_6_mean - lvl_5_mean) * 1000,
            (lvl_7_mean - lvl_6_mean) * 1000,
        ]
    )

    std_measured_step = np.std(
        [
            (lvl_1_mean - lvl_0_mean) * 1000,
            (lvl_2_mean - lvl_1_mean) * 1000,
            (lvl_3_mean - lvl_2_mean) * 1000,
            (lvl_4_mean - lvl_3_mean) * 1000,
            (lvl_5_mean - lvl_4_mean) * 1000,
            (lvl_6_mean - lvl_5_mean) * 1000,
            (lvl_7_mean - lvl_6_mean) * 1000,
        ]
    )

    print(f"Avg Measured Step: {avg_measured_step:.2f}mV")
    print(f"Std Dev of Steps: {std_measured_step:.2f}mV")

    plt.figure(figsize=(10, 6))

    # Plot boxplots for each level to visualize the spread and spacing
    box_data = [data[f"lvl_{i}"] for i in range(8)]
    plt.boxplot(
        box_data,
        positions=range(8),
        patch_artist=True,
        boxprops=dict(facecolor="skyblue", color="black"),
        medianprops=dict(color="red", linewidth=2),
    )

    plt.title("Test 4: V_Cap Voltage Distributions per Weight Level (SG13G2)")
    plt.xlabel("Weight Level (Current Step)")
    plt.ylabel("Stored V_Cap Voltage (V)")
    plt.grid(True, alpha=0.3)
    plt.xticks(range(8), [f"Lvl {i}\n({i * 0.285:.2f}µA)" for i in range(8)])

    plt.show()


if __name__ == "__main__":
    analyze_dc_profiling("test/cim/simulations/test_4_dc_write_profiling.csv")
