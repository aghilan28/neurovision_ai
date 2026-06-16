import pandas as pd
import runpy

# load the Phase6 script WITHOUT executing main()
ns = runpy.run_path("PHASE6_PATIENT_GENERALIZATION_FORENSICS.py")

step16_root_cause = ns["step16_root_cause"]
step17_remediation = ns["step17_remediation"]

conf_df = pd.read_csv("PHASE6_CONFIDENCE_ANALYSIS.csv")
shift_df = pd.read_csv("PHASE6_FEATURE_SHIFT_ANALYSIS.csv")
gvb_df = pd.read_csv("PHASE6_GOOD_VS_BAD_PATIENTS.csv")
imp_shift_df = pd.read_csv("PHASE6_IMPORTANCE_SHIFT_ANALYSIS.csv")
perf_df = pd.read_csv("PHASE6_PATIENT_PERFORMANCE.csv")

try:
    fn_df = pd.read_csv("PHASE5D_FALSE_NEGATIVE_EVENTS.csv")
except:
    fn_df = pd.DataFrame()

print("RUNNING STEP16")

rc_df = step16_root_cause(
    conf_df,
    shift_df,
    fn_df,
    gvb_df
)

print(rc_df.head())

print("RUNNING STEP17")

plan = step17_remediation(
    rc_df,
    conf_df,
    shift_df,
    imp_shift_df,
    fn_df,
    perf_df
)

print("SUCCESS")