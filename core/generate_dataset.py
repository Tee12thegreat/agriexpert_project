"""
One-off generator for the seed crop-recommendation dataset used by
core.ml_advisor. Distributions are loosely based on published
agronomic guidance for each crop's typical N-P-K/pH/climate needs --
this stands in for "historical case data" the expert system starts
with, which the adaptive component then augments with real feedback.

Run with: python core/generate_dataset.py  (from project root, with
DJANGO not required for this script).
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

# crop: (N_mean,N_sd, P_mean,P_sd, K_mean,K_sd, temp_mean,temp_sd,
#        humidity_mean,humidity_sd, ph_mean,ph_sd, rainfall_mean,rainfall_sd)
PROFILES = {
    "maize":   (90, 12, 45, 8, 40, 8, 24, 3, 60, 8, 6.2, 0.4, 90, 20),
    "tomato":  (70, 10, 55, 8, 60, 10, 23, 3, 65, 8, 6.4, 0.3, 70, 15),
    "beans":   (40, 8, 60, 8, 45, 8, 20, 3, 65, 8, 6.0, 0.4, 80, 18),
    "cabbage": (100, 12, 50, 8, 70, 10, 18, 3, 75, 8, 6.5, 0.3, 60, 12),
    "potato":  (80, 10, 60, 8, 100, 12, 17, 3, 70, 8, 5.8, 0.4, 65, 15),
    "rice":    (95, 12, 40, 8, 40, 8, 27, 2, 82, 6, 6.0, 0.4, 200, 25),
    "cotton":  (60, 10, 35, 8, 50, 8, 27, 3, 55, 8, 6.8, 0.4, 55, 15),
}

N_PER_CROP = 90


def sample_crop(name, params):
    (n_m, n_s, p_m, p_s, k_m, k_s, t_m, t_s, h_m, h_s, ph_m, ph_s, r_m, r_s) = params
    rows = {
        "N": RNG.normal(n_m, n_s, N_PER_CROP).clip(0, None),
        "P": RNG.normal(p_m, p_s, N_PER_CROP).clip(0, None),
        "K": RNG.normal(k_m, k_s, N_PER_CROP).clip(0, None),
        "temperature": RNG.normal(t_m, t_s, N_PER_CROP),
        "humidity": RNG.normal(h_m, h_s, N_PER_CROP).clip(0, 100),
        "ph": RNG.normal(ph_m, ph_s, N_PER_CROP).clip(3.5, 9.0),
        "rainfall": RNG.normal(r_m, r_s, N_PER_CROP).clip(0, None),
    }
    df = pd.DataFrame(rows)
    df["label"] = name
    return df


def main():
    frames = [sample_crop(name, params) for name, params in PROFILES.items()]
    full = pd.concat(frames, ignore_index=True)
    full = full.sample(frac=1.0, random_state=1).reset_index(drop=True)
    full = full.round(2)
    full.to_csv("core/data/crop_dataset.csv", index=False)
    print(f"Wrote {len(full)} rows to core/data/crop_dataset.csv")


if __name__ == "__main__":
    main()
