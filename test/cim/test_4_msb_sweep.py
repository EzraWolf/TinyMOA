"""
Find optimal MSB current write level since
- higher MSB write = higher V_Cap for larger  LSB steps (higher SNR) but worse V_Cap  retention
- lower  MSB write = lower  V_Cap for smaller LSB steps (lower  SNR) but better V_Cap retention
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def analyze_retention_sweep(file_path):
    CURRENT_DIR = os.getcwd()
    file_path = os.path.join(CURRENT_DIR, file_path)

    cols = ["i_target", "v_settle", "v_thresh", "t_fail"]
    data = pd.read_csv(file_path, sep=r"\s+", header=None, names=cols)

    data["i_target_uA"] = (
        data["i_target"].astype(str).str.replace("u", "").astype(float)
    )
    data["t_fail_us"] = data["t_fail"] * 1e6

    unique_currents = data["i_target_uA"].unique()

    print("Monte Carlo Results for MSB Sweep:")
    print(
        f"{'I_BL (uA)':<10} | {'Mean MSB (mV)':<15} | {'Half-LSB (mV)':<15} | {'Mean Ret (us)':<15} | {'Sig Ret (us)':<15} | {'3-Sig Ret (us)':<15}"
    )

    plot_data = []

    for current in unique_currents:
        subset = data[data["i_target_uA"] == current]

        mean_msb = subset["v_settle"].mean() * 1000
        mean_thresh_drop = (
            subset["v_settle"].mean() - subset["v_thresh"].mean()
        ) * 1000

        mean_ret = subset["t_fail_us"].mean()
        std_ret = subset["t_fail_us"].std()
        realistic_ret = mean_ret - (3 * std_ret)

        print(
            f"{current:<10.1f} | {mean_msb:<15.2f} | {mean_thresh_drop:<15.2f} | {mean_ret:<15.2f} | {std_ret:<15.2f} | {realistic_ret:<15.2f}"
        )
        plot_data.append(subset["t_fail_us"].dropna())

    plt.figure(figsize=(10, 6))
    plt.boxplot(
        plot_data,
        positions=unique_currents,
        patch_artist=True,
        boxprops=dict(facecolor="skyblue", color="black"),
        medianprops=dict(color="red", linewidth=2),
    )

    plt.axhline(
        100.0, color="black", linestyle="--", label="100us Target (5000 Cycles)"
    )
    plt.title("Test 4: Retention Time by Write Current (SG13G2)")
    plt.xlabel("Write Current I_BL (uA)")
    plt.ylabel("Time to Fail (us) [Drops > Half-LSB]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.show()


if __name__ == "__main__":
    analyze_retention_sweep("test/cim/simulations/test_4_retention_sweep.csv")
