from pathlib import Path
from statistics import mean, pstdev, quantiles

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from processes import calculate_usage, flatten_meters, load_json_file


BASE_DIR = Path(__file__).resolve().parent


def build_electric_usage_series():
    info = load_json_file(BASE_DIR / "basic_info.json")
    prev_meter = load_json_file(BASE_DIR / "previous_meter.json")
    curr_meter = load_json_file(BASE_DIR / "current_meter.json")

    prev_electric = flatten_meters(prev_meter.get("electric", []))
    curr_electric = flatten_meters(curr_meter.get("electric", []))

    room_numbers = list(info.get("rooms_config", {}).keys())
    usage_series = []

    for unit_number in room_numbers:
        previous_value = prev_electric.get(unit_number, 0)
        current_value = curr_electric.get(unit_number, 0)
        usage_series.append(
            (unit_number, calculate_usage(previous_value, current_value))
        )

    return usage_series


def filter_usage_outliers(usage_series):
    values = [usage for _, usage in usage_series]
    if len(values) < 4:
        return usage_series, [], 0.0, 0.0

    q1, _, q3 = quantiles(values, n=4, method="inclusive")
    iqr = q3 - q1
    lower_bound = max(0.0, q1 - 1.5 * iqr)
    upper_bound = q3 + 1.5 * iqr

    filtered_series = [
        (unit, usage)
        for unit, usage in usage_series
        if lower_bound <= usage <= upper_bound
    ]
    excluded_series = [
        (unit, usage)
        for unit, usage in usage_series
        if usage < lower_bound or usage > upper_bound
    ]

    if not filtered_series:
        return usage_series, [], lower_bound, upper_bound

    return filtered_series, excluded_series, lower_bound, upper_bound


def plot_electric_usage(usage_series, output_path):
    filtered_series, excluded_series, lower_bound, upper_bound = filter_usage_outliers(
        usage_series
    )
    values = [usage for _, usage in filtered_series]

    avg_value = mean(values) if values else 0.0
    sd_value = pstdev(values) if len(values) > 1 else 0.0

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(20, 8), gridspec_kw={"width_ratios": [3, 1]})

    ax_hist.hist(values, bins=min(18, max(6, len(values) // 6)), color="#2E86AB", edgecolor="white", alpha=0.9)
    ax_hist.axvline(avg_value, color="#C0392B", linewidth=2, linestyle="--", label=f"Mean: {avg_value:.2f}")
    ax_hist.axvline(avg_value + sd_value, color="#27AE60", linewidth=1.5, linestyle=":", label=f"Mean + SD: {avg_value + sd_value:.2f}")
    ax_hist.axvline(max(avg_value - sd_value, 0), color="#27AE60", linewidth=1.5, linestyle=":", label=f"Mean - SD: {max(avg_value - sd_value, 0):.2f}")
    ax_hist.axvspan(max(avg_value - sd_value, 0), avg_value + sd_value, color="#27AE60", alpha=0.12)
    ax_hist.set_title("Electric Usage Distribution")
    ax_hist.set_xlabel("Electric usage (units)")
    ax_hist.set_ylabel("Number of rooms")
    ax_hist.grid(axis="y", linestyle="--", alpha=0.25)
    ax_hist.legend(loc="upper right")

    ax_box.boxplot(values, vert=True, patch_artist=True, boxprops={"facecolor": "#F39C12", "alpha": 0.75})
    ax_box.set_title("Box Plot")
    ax_box.set_xticks([1])
    ax_box.set_xticklabels(["Rooms"])
    ax_box.grid(axis="y", linestyle="--", alpha=0.25)

    fig.suptitle("Electric Usage Distribution by Room", fontsize=16, y=0.98)

    summary_text = [
        f"Rooms analyzed: {len(filtered_series)}",
        f"Excluded outliers: {len(excluded_series)}",
        f"IQR lower bound: {lower_bound:.2f}",
        f"IQR upper bound: {upper_bound:.2f}",
        f"Mean: {avg_value:.2f}",
        f"SD: {sd_value:.2f}",
    ]
    fig.text(
        0.01,
        0.01,
        "\n".join(summary_text),
        ha="left",
        va="bottom",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "alpha": 0.95, "edgecolor": "#D5D8DC"},
    )

    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    return avg_value, sd_value, excluded_series


def main():
    usage_series = build_electric_usage_series()
    output_path = BASE_DIR / "electric_usage_plot.png"
    avg_value, sd_value, excluded_series = plot_electric_usage(usage_series, output_path)

    print(f"Saved plot to: {output_path}")
    print(f"Rooms analyzed: {len(usage_series)}")
    print(f"Mean electric usage: {avg_value:.2f}")
    print(f"Standard deviation: {sd_value:.2f}")
    print(f"Excluded outliers: {len(excluded_series)}")
    for unit_number, usage in excluded_series:
        print(f"- {unit_number}: {usage}")


if __name__ == "__main__":
    main()