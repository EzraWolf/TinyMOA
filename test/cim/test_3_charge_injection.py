import os
import pandas as pd
import matplotlib.pyplot as plt


def analyze_charge_injection(file_path):
    CURRENT_DIR = os.getcwd()
    file_path = os.path.join(CURRENT_DIR, file_path)
    data = pd.read_csv(file_path, sep=r"\s+", header=None, names=["index", "delta_v"])

    # 1200mV / 3bit - 1 precision = ~171,4mV to represent the LSB
    # Halve LSB voltage since that is the threshold, so ~85,7mV is the error budget for any and all noise sources including charge injection
    lsb_budget_mv = 1200 / (2**3 - 1)
    lsb_budget_threshold_mv = lsb_budget_mv / 2
    mean_drop = data["delta_v"].mean()
    std_v = data["delta_v"].std()

    print(f"Monte Carlo Results for Charge Injection:")
    print(f"3-bit LSB Voltage: {lsb_budget_mv:.2f}mV")
    print(f"LSB Threshold:     {lsb_budget_threshold_mv:.2f}mV")
    print(f"Mean Drop:         {mean_drop * 1000:.2f}mV")
    print(f"Std. Deviation:    {std_v * 1000:.2f}mV")
    print(f"3-Sigma Variation: {3 * std_v * 1000:.2f}mV")
    print(f"Worst Case: {(mean_drop + 3 * std_v) * 1000:.2f}mV")

    if (mean_drop + 3 * std_v) * 1000 > lsb_budget_threshold_mv:
        print(
            f"CRITICAL: Injection exceeds {lsb_budget_threshold_mv:.2f}mV error budget. Must stall until settled or redesign."
        )
    else:
        print("PASS: Injection within 3-bit precision limits.")

    plt.figure(figsize=(10, 6))
    plt.hist(data["delta_v"] * 1000, bins=30, color="salmon", edgecolor="black")
    plt.axvline(
        lsb_budget_threshold_mv,
        color="black",
        linestyle="--",
        label=f"{lsb_budget_threshold_mv:.2f}mV Error Limit",
    )
    plt.title("Test 3: Charge Injection Distribution (SG13G2)")
    plt.xlabel("Voltage Drop (mV)")
    plt.ylabel("Samples")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()


if __name__ == "__main__":
    analyze_charge_injection("test/cim/simulations/test_3_charge_injection.csv")
