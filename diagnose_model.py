import joblib

model_path = r"E:\Project\neurovision_ai\PHASE5B_TEMPORAL_XGBOOST.joblib"
print("Loading model...")
model = joblib.load(model_path)

# Extract the underlying booster names
booster = model.get_booster()
feature_names = booster.feature_names

if feature_names:
    print(f"SUCCESS! Found all {len(feature_names)} feature keys.")
    output_path = "expected_484_features.txt"
    with open(output_path, "w") as f:
        f.write("\n".join(feature_names))
    print(f"Saved the master feature checklist to: {output_path}")
else:
    print("The model booster lacks named strings. Printing structural feature map...")
    # Alternative extraction method
    f_score = booster.get_fscore()
    print(f"Found {len(f_score)} active split features in the trees.")
    with open("model_fscores.txt", "w") as f:
        for k, v in sorted(f_score.items()):
            f.write(f"{k}: {v}\n")