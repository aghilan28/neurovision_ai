import json, os, sys, traceback
repo = r"C:\Users\AKILA\OneDrive\ドキュメント\neurovision\neurovision_ai"
sys.path.insert(0, repo)
sys.path.insert(0, os.path.join(repo, "tests"))
state = {}
try:
    from _track3_helpers import real_chb_mit_root
    root = real_chb_mit_root()
    state["real_chb_mit_root"] = root
    if root:
        state["root_exists"] = os.path.exists(root)
        chb = os.path.join(root, "chb_mit", "chb01")
        state["chb01_path"] = chb
        state["chb01_exists"] = os.path.exists(chb)
        if os.path.exists(chb):
            entries = sorted(os.listdir(chb))
            state["chb01_entries"] = entries
            state["chb01_edf_files"] = sorted(f for f in entries if f.lower().endswith(".edf"))
        for rel in ["chb_mit", os.path.join("chb_mit", "chb01"), os.path.join("chb_mit", "chb01", "chb01_01.edf"), os.path.join("chb_mit", "chb01", "chb01_03.edf")]:
            p = os.path.join(root, rel)
            state["exists:" + rel] = os.path.exists(p)
            if os.path.exists(p) and os.path.isfile(p):
                state["size:" + rel] = os.path.getsize(p)
except Exception:
    state["real_chb_mit_root_error"] = traceback.format_exc()
try:
    from backend.dataset_acquisition import RealDatasetService, DatasetSource
    if state.get("real_chb_mit_root"):
        svc = RealDatasetService(data_root=state["real_chb_mit_root"])
        out = svc.integrate(DatasetSource.CHB_MIT, allow_download=False)
        state["dataset_ready_for_training"] = getattr(out, "ready_for_training", None)
        rec = getattr(out, "dataset_record", None)
        state["dataset_record"] = rec.to_dict() if rec is not None and hasattr(rec, "to_dict") else str(rec)
        for attr in ["acquisition", "validation", "label_verification", "inventory", "readiness"]:
            val = getattr(out, attr, None)
            state["dataset_" + attr] = val.to_dict() if val is not None and hasattr(val, "to_dict") else str(val)
        state["dataset_lineage_id"] = getattr(out, "lineage_id", None)
        state["dataset_registry_lineage_id"] = getattr(out, "registry_lineage_id", None)
        state["dataset_audit_head"] = getattr(out, "audit_head", None)
        state["dataset_audit_verify"] = svc.audit.verify() if hasattr(svc, "audit") else None
except Exception:
    state["dataset_probe_error"] = traceback.format_exc()
try:
    from backend.real_model_training import RealModelTrainingService
    if state.get("real_chb_mit_root"):
        svc = RealModelTrainingService(data_root=state["real_chb_mit_root"])
        out = svc.develop(allow_download=False, window_seconds=4.0, background_per_seizure=4)
        state["training_dataset_record"] = out.dataset_record.to_dict() if hasattr(out.dataset_record, "to_dict") else str(out.dataset_record)
        state["training_ready_models"] = [m.model_id for m in out.ready_models()] if hasattr(out, "ready_models") else None
        state["training_model_records"] = [m.to_dict() if hasattr(m, "to_dict") else str(m) for m in getattr(out, "models", [])]
        state["training_benchmarks"] = [b.to_dict() if hasattr(b, "to_dict") else str(b) for b in getattr(out, "benchmarks", [])]
        state["training_audit_verify"] = svc.audit.verify() if hasattr(svc, "audit") else None
except Exception:
    state["training_probe_error"] = traceback.format_exc()
print(json.dumps(state, indent=2, default=str))
