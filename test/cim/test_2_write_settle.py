import os
import pandas as pd
import matplotlib.pyplot as plt


def analyze_write_settle(file_path):
    CURRENT_DIR = os.getcwd()
    file_path = os.path.join(CURRENT_DIR, file_path)
    data = pd.read_csv(file_path, sep=r"\s+", header=None, names=["index", "v_cap"])

    mean_v = data["v_cap"].mean()
    std_v = data["v_cap"].std()

    print(f"Monte Carlo Results for Write Settling:")
    print(f"Mean V_Cap: {mean_v:.4f} V")
    print(f"Std. Deviation: {std_v * 1000:.2f} mV")
    print(f"3-Sigma Variation: {3 * std_v * 1000:.2f} mV")

    plt.figure(figsize=(10, 6))
    plt.hist(data["v_cap"], bins=30, color="skyblue", edgecolor="black")
    plt.axvline(
        mean_v,
        color="red",
        linestyle="dashed",
        linewidth=2,
        label=f"Mean: {mean_v:.3f}V",
    )
    plt.title("Distribution of Settled Cap_TP Voltage (Test 2)")
    plt.xlabel("Voltage (V)")
    plt.ylabel("Samples")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()


if __name__ == "__main__":
    analyze_write_settle("test/cim/simulations/test_2_write_settle.csv")
