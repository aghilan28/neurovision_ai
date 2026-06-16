import pandas as pd
import math

conf_df = pd.read_csv("PHASE6_CONFIDENCE_ANALYSIS.csv")
shift_df = pd.read_csv("PHASE6_FEATURE_SHIFT_ANALYSIS.csv")

print("CONF OK", conf_df.shape)
print("SHIFT OK", shift_df.shape)

for pat in ["chb14", "chb22", "chb02"]:
    print("\nPATIENT:", pat)

    row = conf_df.set_index("patient").loc[pat]

    print("max_prob", float(row["prob_max_positive"]))

    pat_shift = shift_df[shift_df["patient"] == pat]

    print(
        "high_shift_count",
        int((pat_shift["ks_statistic"] > 0.3).sum())
    )

    print(
        "mean_shift",
        float(pat_shift["ks_statistic"].mean())
    )

print("STEP16 LOGIC PASSED")

print("STEP15 DONE")
print(conf_df.shape)

rc_df = step16_root_cause(conf_df, shift_df, fn_df, gvb_df)

print("STEP16 DONE")
print(rc_df.shape)

step17_remediation(
    rc_df,
    conf_df,
    shift_df,
    imp_shift_df,
    fn_df,
    perf_df
)

print("STEP17 DONE")