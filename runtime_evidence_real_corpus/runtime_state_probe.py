import json, os, traceback
state = {}
try:
    from tests._track3_helpers import real_chb_mit_root
except Exception:
    try:
        from _track3_helpers import real_chb_mit_root
    except Exception as exc:
        state["real_chb_mit_root_import_error"] = traceback.format_exc()
        real_chb_mit_root = None
if real_chb_mit_root:
    root = real_chb_mit_root()
    state["real_chb_mit_root"] = root
    if root:
        state["root_exists"] = os.path.exists(root)
        chb = os.path.join(root, "chb_mit", "chb01")
        state["chb01_path"] = chb
        state["chb01_exists"] = os.path.exists(chb)
        if os.path.exists(chb):
            state["chb01_entries"] = sorted(os.listdir(chb))
            state["chb01_edf_files"] = sorted(f for f in os.listdir(chb) if f.lower().endswith(".edf"))
        for rel in ["chb_mit", os.path.join("chb_mit", "chb01"), os.path.join("chb_mit", "chb01", "chb01_01.edf"), os.path.join("chb_mit", "chb01", "chb01_03.edf")]:
            p = os.path.join(root, rel)
            state["exists:" + rel] = os.path.exists(p)
            if os.path.exists(p) and os.path.isfile(p):
                state["size:" + rel] = os.path.getsize(p)
try:
    from backend.dataset_acquisition import RealDatasetService, DatasetSource
    if state.get("real_chb_mit_root"):
        svc = RealDatasetService(data_root=state["real_chb_mit_root"])
        out = svc.integrate(DatasetSource.CHB_MIT, allow_download=False)
        state["dataset_outcome"] = out.to_dict() if hasattr(out, "to_dict") else str(out)
        state["dataset_ready_for_training"] = getattr(out, "ready_for_training", None)
        state["dataset_record"] = out.dataset_record.to_dict() if getattr(out, "dataset_record", None) and hasattr(out.dataset_record, "to_dict") else str(getattr(out, "dataset_record", None))
        state["dataset_registry_size"] = len(getattr(svc.registry, "records", lambda: [])()) if hasattr(svc.registry, "records") else None
        state["dataset_audit_verify"] = svc.audit.verify() if hasattr(svc, "audit") else None
except Exception:
    state["dataset_probe_error"] = traceback.format_exc()
try:
    from backend.real_model_training import RealModelTrainingService
    if state.get("real_chb_mit_root"):
        svc = RealModelTrainingService(data_root=state["real_chb_mit_root"])
        out = svc.develop(allow_download=False, window_seconds=4.0, background_per_seizure=4)
        state["training_outcome"] = out.to_dict() if hasattr(out, "to_dict") else str(out)
        state["training_ready_models"] = [m.model_id for m in out.ready_models()] if hasattr(out, "ready_models") else None
        state["training_audit_verify"] = svc.audit.verify() if hasattr(svc, "audit") else None
except Exception:
    state["training_probe_error"] = traceback.format_exc()
print(json.dumps(state, indent=2, default=str))
