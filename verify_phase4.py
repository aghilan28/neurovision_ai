#!/usr/bin/env python3
"""End-to-end verifier for Phase 4 — hits calibrate+predict+analysis for each EDF
and prints a summary showing the report responds to different inputs."""
import json, sys, time, urllib.request, urllib.parse, os

API = "http://127.0.0.1:8080"


def post_multipart(path, filepath):
    boundary = "----NeuroVisionBoundary7MA4YWxkTrZu0gW"
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        API + path, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def get_json(path):
    with urllib.request.urlopen(API + path, timeout=30) as resp:
        return json.loads(resp.read().decode())


def run_file(label, path):
    print(f"\n{'='*70}\n  FILE: {label}  ({path})\n{'='*70}")
    cal = post_multipart("/api/v1/calibrate", path)
    assert cal.get("status") == "SUCCESS", f"calibrate failed: {cal}"
    pred = post_multipart("/api/v1/predict", path)
    assert pred.get("status") == "SUCCESS", f"predict failed: {pred}"
    aid = pred["analysis_id"]
    rep = get_json(f"/api/v1/analysis/{urllib.parse.quote(aid)}")

    r = rep.get("risk", {})
    bi = rep.get("brain_intelligence", {}) or {}
    si = rep.get("signal_intelligence", {}) or {}
    loc = bi.get("localization", {}) or {}
    sd = bi.get("spectral_dominance", {}) or {}
    m = rep.get("metadata", {}) or {}
    bands = {b["name"]: b["value"] for b in sd.get("bands", [])}

    print(f"  analysis_id       : {aid}")
    print(f"  patient_id        : {rep.get('patient_id')}")
    print(f"  filename          : {rep.get('filename')}")
    print(f"  timestamp         : {rep.get('timestamp')}")
    print(f"  channels (cal/pred): {cal.get('channels')} / {m.get('channels')}  (must match)")
    print(f"  duration          : {m.get('duration_seconds')} s")
    print(f"  sampling_rate     : {m.get('sampling_rate_hz')} Hz")
    print(f"  seizure prob      : {r.get('probability')}%  tier={r.get('tier')}")
    print(f"  model_confidence  : {r.get('model_confidence')}%")
    print(f"  pred_stability    : {r.get('prediction_stability')}%")
    print(f"  latency           : {r.get('analysis_latency_seconds')} s")
    print(f"  dominant zone/lead: {loc.get('dominant_zone')} / {loc.get('dominant_lead')}")
    print(f"  loc_confidence    : {loc.get('confidence')}%  evidence={loc.get('evidence_strength')}")
    print(f"  spectral label    : {sd.get('label')}")
    print(f"  bands %           : DELTA={bands.get('DELTA')} THETA={bands.get('THETA')} ALPHA={bands.get('ALPHA')} BETA={bands.get('BETA')}")
    print(f"  quality           : {si.get('quality_score')}/100 ({si.get('quality_label')})")
    print(f"  noise_burden      : {si.get('noise_burden')}")
    print(f"  artifact_burden   : {si.get('artifact_burden')}")
    print(f"  trust_level       : {si.get('trust_level')}%")
    print(f"  similar_cases     : {len((rep.get('case_intelligence') or {}).get('similar_cases') or [])}")
    print(f"  key_finding       : {(r.get('key_finding') or '')[:110]}...")

    # Cross-validate consistency with upload
    assert cal.get("channels") == m.get("channels"), f"channel mismatch: cal={cal.get('channels')} report={m.get('channels')}"
    assert abs(float(cal.get("sampling_rate", 0)) - float(m.get("sampling_rate_hz", 0))) < 0.5, "sr mismatch"
    assert abs(float(cal.get("execution_time_seconds", 0)) - float(m.get("duration_seconds", 0))) < 1.0, "duration mismatch"
    print("  [OK] Upload-page ↔ Report-page consistency: CHANNELS / SR / DURATION all match")
    return rep


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    files = [
        ("CHB-MIT chb01_01 (seizure file)", "chb_test/chb01/chb01_01.edf"),
        ("synthetic valid.edf (3 ch, no sz)", "tests/fixtures/eeg/valid.edf"),
        ("synthetic valid_edf_plus", "tests/fixtures/eeg/valid_edf_plus.edf"),
        ("workspace valid_1.edf", "workspace/raw/d3e5ab4361cfe73d/valid_1.edf"),
        ("workspace valid_2.edf", "workspace/raw/e1e43937d7875e1e/valid_2.edf"),
    ]
    results = []
    for label, p in files:
        if os.path.exists(p):
            try:
                results.append(run_file(label, p))
            except Exception as e:
                print(f"  !! FAIL for {p}: {e}")
        else:
            print(f"\n  (skip) {p} not found")

    # Verify values differ across files (not hardcoded)
    print(f"\n{'='*70}\n  CROSS-FILE VARIATION CHECK\n{'='*70}")
    probs = {r["filename"]: r["risk"]["probability"] for r in results}
    zones = {r["filename"]: r["brain_intelligence"]["localization"]["dominant_zone"] for r in results}
    qs = {r["filename"]: r["signal_intelligence"]["quality_score"] for r in results}
    print("  probs:", probs)
    print("  zones:", zones)
    print("  quality:", qs)
    assert len(set(probs.values())) > 1 or len(results) <= 1, "Probabilities are identical across files (hardcoded?)"
    print("  [OK] Values vary across EDF inputs — report is driven by real data.")
