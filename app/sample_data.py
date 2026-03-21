from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_sample_measurements() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    position = np.linspace(0.0, 200.0, 2001)
    direction = np.where((np.arange(len(position)) // 250) % 2 == 0, 1.0, -1.0)
    velocity = 120.0 + 30.0 * np.sin(2.0 * np.pi * position / 80.0)
    temperature = 20.0 + 1.2 * np.sin(2.0 * np.pi * position / 180.0)

    long_error_mm = (
        0.0006 * np.sin(2.0 * np.pi * position / 160.0)
        + 0.0004 * (position / position.max()) ** 2
    )
    cyclic_error_mm = (
        0.006 * np.sin(2.0 * np.pi * position / 2.0 + 0.2)
        + 0.0025 * np.cos(4.0 * np.pi * position / 2.0 - 0.5)
    )
    dynamic_error_mm = 0.00001 * velocity + 0.0008 * direction
    thermal_error_mm = 0.0012 * (temperature - 20.0)
    noise_mm = rng.normal(0.0, 0.0008, size=len(position))

    reference_position = position
    sensor_position = (
        reference_position
        + long_error_mm
        + cyclic_error_mm
        + dynamic_error_mm
        + thermal_error_mm
        + noise_mm
    )

    return pd.DataFrame(
        {
            "position_mm": position,
            "sensor_position_mm": sensor_position,
            "reference_position_mm": reference_position,
            "velocity_mm_s": velocity,
            "temperature_c": temperature,
            "direction": direction,
        }
    )


def main() -> None:
    output_dir = Path("data")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "sample_measurements.csv"
    generate_sample_measurements().to_csv(output_path, index=False)
    print(f"示例数据已生成: {output_path}")


if __name__ == "__main__":
    main()

