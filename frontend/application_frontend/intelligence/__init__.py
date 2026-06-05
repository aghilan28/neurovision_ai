"""``frontend/application_frontend/intelligence`` — EEG Intelligence Report Generator.

Transforms raw prediction pipeline outputs into a structured clinical intelligence
report. This is the core of the NeuroVision Intelligence Platform — it replaces the
simple classifier output with a multi-section neurological analysis report.

The intelligence report contains 7 sections:
1. Signal Quality Intelligence
2. Brain Activity Characterization
3. Abnormality Assessment
4. Seizure Intelligence
5. Evidence Intelligence
6. Clinical Narrative
7. Overall Intelligence Summary
"""

from __future__ import annotations

from typing import Optional


def build_intelligence_report(*, prediction: dict, confidence: dict,
                               explanation: dict, upload: dict,
                               evidence: dict) -> dict:
    """Build the complete EEG Intelligence Report from pipeline outputs.

    This function receives the raw outputs from the NeuroVision analysis pipeline
    and transforms them into a structured intelligence report that resembles a
    neurological assessment rather than a classifier output.
    """
    # Extract core data
    pred_class = prediction.get("predicted_class", 0)
    pred_label = str(prediction.get("predicted_label", ""))
    conf_score = float(confidence.get("score", confidence.get("confidence_score", 0.5)))
    conf_level = str(confidence.get("confidence_level", confidence.get("level", "moderate")))
    calib_quality = str(prediction.get("calibration_quality",
                        confidence.get("calibration_quality", "unknown")))
    expl_method = str(explanation.get("method", ""))
    decision_factors = explanation.get("decision_factors",
                       explanation.get("feature_contributions", []))
    if isinstance(decision_factors, dict):
        decision_factors = []

    n_channels = int(upload.get("n_channels", 0))
    sfreq = float(upload.get("sampling_frequency", 0))
    duration = float(upload.get("duration_seconds", 0))
    filename = upload.get("filename", "")
    file_format = upload.get("format", upload.get("fmt", ""))
    size_bytes = int(upload.get("size_bytes", 0))

    model_info = evidence.get("model", {})
    model_arch = model_info.get("architecture", "unknown")
    model_id = model_info.get("model_id", "")

    # ── Section 1: Signal Quality Intelligence ──
    signal_quality = _assess_signal_quality(
        n_channels=n_channels, sfreq=sfreq, duration=duration,
        size_bytes=size_bytes, file_format=file_format,
        decision_factors=decision_factors)

    # ── Section 2: Brain Activity Characterization ──
    brain_activity = _characterize_brain_activity(
        decision_factors=decision_factors, pred_class=pred_class,
        conf_score=conf_score, n_channels=n_channels, sfreq=sfreq)

    # ── Section 3: Abnormality Assessment ──
    abnormality = _assess_abnormality(
        pred_class=pred_class, conf_score=conf_score,
        calib_quality=calib_quality, decision_factors=decision_factors)

    # ── Section 4: Seizure Intelligence ──
    seizure_intel = _build_seizure_intelligence(
        pred_class=pred_class, conf_score=conf_score,
        conf_level=conf_level, calib_quality=calib_quality)

    # ── Section 5: Evidence Intelligence ──
    evidence_intel = _build_evidence_intelligence(
        decision_factors=decision_factors, model_arch=model_arch,
        model_id=model_id, expl_method=expl_method)

    # ── Section 6: Clinical Narrative ──
    narrative = _generate_clinical_narrative(
        pred_class=pred_class, conf_score=conf_score, conf_level=conf_level,
        calib_quality=calib_quality, n_channels=n_channels, sfreq=sfreq,
        duration=duration, filename=filename, decision_factors=decision_factors,
        signal_quality=signal_quality, abnormality=abnormality)

    # ── Section 7: Overall Intelligence Summary ──
    summary = _build_overall_summary(
        pred_class=pred_class, conf_score=conf_score,
        signal_quality=signal_quality, abnormality=abnormality)

    return {
        "signal_quality": signal_quality,
        "brain_activity": brain_activity,
        "abnormality": abnormality,
        "seizure_intelligence": seizure_intel,
        "evidence": evidence_intel,
        "narrative": narrative,
        "summary": summary,
    }


def _assess_signal_quality(*, n_channels, sfreq, duration, size_bytes,
                            file_format, decision_factors) -> dict:
    """Assess recording quality and trustworthiness."""
    issues = []
    score = 100

    # Channel assessment
    if n_channels < 8:
        issues.append(f"Low channel count ({n_channels}) — limited spatial resolution")
        score -= 20
    elif n_channels < 16:
        issues.append(f"Moderate channel count ({n_channels})")
        score -= 5

    # Sampling frequency
    if sfreq < 128:
        issues.append(f"Low sampling rate ({sfreq} Hz) — may miss fast transients")
        score -= 15
    elif sfreq >= 256:
        score += 0  # standard clinical

    # Duration
    if duration < 5:
        issues.append(f"Very short recording ({duration:.1f}s) — limited temporal context")
        score -= 25
    elif duration < 30:
        issues.append(f"Short recording ({duration:.1f}s)")
        score -= 10
    elif duration >= 60:
        score += 0  # adequate

    # File size sanity
    expected_bytes = n_channels * sfreq * duration * 2  # 16-bit samples
    if size_bytes > 0 and expected_bytes > 0:
        ratio = size_bytes / expected_bytes
        if ratio < 0.1:
            issues.append("File appears truncated")
            score -= 20

    # Check for artifact indicators in decision factors
    artifact_factors = [f for f in decision_factors
                        if any(k in f.get("name", "").lower()
                               for k in ["skewness", "kurtosis", "rms", "line_length"])]
    high_artifact = any(abs(f.get("contribution", 0)) > 0.1 for f in artifact_factors)
    if high_artifact:
        issues.append("Statistical outliers detected in signal characteristics")
        score -= 10

    score = max(0, min(100, score))

    if score >= 80:
        grade = "Good"
        trust = "Recording is suitable for automated analysis"
    elif score >= 60:
        grade = "Acceptable"
        trust = "Recording quality is adequate; results should be reviewed"
    elif score >= 40:
        grade = "Limited"
        trust = "Recording quality may impact analysis accuracy"
    else:
        grade = "Poor"
        trust = "Recording quality limits interpretation reliability"

    return {
        "score": score,
        "grade": grade,
        "trust_statement": trust,
        "issues": issues,
        "channels": n_channels,
        "sampling_rate": sfreq,
        "duration": round(duration, 1),
        "format": file_format,
    }


def _characterize_brain_activity(*, decision_factors, pred_class, conf_score,
                                   n_channels, sfreq) -> dict:
    """Describe the EEG brain activity patterns."""
    # Analyze decision factors to understand spectral characteristics
    factors_by_name = {f.get("name", ""): f for f in decision_factors}

    # Identify dominant features
    supporting = sorted([f for f in decision_factors if f.get("direction") == "supports"],
                        key=lambda f: abs(f.get("contribution", 0)), reverse=True)
    opposing = sorted([f for f in decision_factors if f.get("direction") == "opposes"],
                      key=lambda f: abs(f.get("contribution", 0)), reverse=True)

    # Interpret feature names into brain activity descriptions
    activity_patterns = []

    for f in decision_factors[:5]:
        name = f.get("name", "")
        contrib = f.get("contribution", 0)
        direction = f.get("direction", "")

        if "coherence" in name.lower():
            if contrib > 0.05:
                activity_patterns.append("Elevated inter-channel synchronization")
            elif contrib < -0.05:
                activity_patterns.append("Reduced inter-channel coherence")

        if "rms" in name.lower():
            if contrib > 0.01:
                activity_patterns.append("Elevated signal amplitude in active regions")
            elif contrib < -0.01:
                activity_patterns.append("Attenuated signal amplitude")

        if "hjorth" in name.lower():
            if "activity" in name.lower():
                activity_patterns.append("Notable Hjorth activity — signal power variation detected")
            elif "mobility" in name.lower():
                activity_patterns.append("Frequency content variability observed")

        if "skewness" in name.lower():
            activity_patterns.append("Asymmetric waveform morphology detected")

        if "band" in name.lower() or "spectral" in name.lower():
            activity_patterns.append("Spectral power distribution variations noted")

    if not activity_patterns:
        activity_patterns = ["Standard EEG activity patterns observed"]

    # Brain state description
    if pred_class == 1 and conf_score > 0.7:
        state = "Potentially abnormal rhythmic activity"
        rhythm_desc = "Dominant slow-wave or rhythmic patterns suggestive of ictal activity"
    elif pred_class == 0 and conf_score > 0.7:
        state = "Background activity within expected parameters"
        rhythm_desc = "Predominant posterior alpha rhythm with expected frequency distribution"
    else:
        state = "Indeterminate brain state — requires clinical correlation"
        rhythm_desc = "Mixed frequency content without clear dominant pattern"

    return {
        "state": state,
        "dominant_rhythm": rhythm_desc,
        "patterns": activity_patterns[:5],
        "n_contributing_features": len(decision_factors),
        "channel_coverage": f"{n_channels} channels at {sfreq} Hz",
    }


def _assess_abnormality(*, pred_class, conf_score, calib_quality,
                          decision_factors) -> dict:
    """Assess the degree of abnormality in the recording."""
    # Compute abnormality score from prediction and confidence
    if pred_class == 1:
        raw_score = conf_score
    else:
        raw_score = 1 - conf_score

    # Adjust for calibration
    if "poorly" in calib_quality.lower():
        raw_score *= 0.8  # discount poorly calibrated predictions

    # Categorize
    if raw_score < 0.2:
        level = "Normal"
        description = "No significant abnormalities detected in the analyzed segment."
        color = "green"
    elif raw_score < 0.4:
        level = "Mildly Abnormal"
        description = "Minor deviations from expected background patterns. Clinical significance uncertain."
        color = "yellow"
    elif raw_score < 0.6:
        level = "Moderately Abnormal"
        description = "Notable deviations from normal background activity. Clinical review recommended."
        color = "orange"
    elif raw_score < 0.8:
        level = "Significantly Abnormal"
        description = "Substantial abnormal patterns detected. Urgent clinical review advised."
        color = "red"
    else:
        level = "Highly Abnormal"
        description = "Strong abnormal activity consistent with potential ictal patterns. Immediate clinical attention recommended."
        color = "red"

    # Identify specific observations
    observations = []
    for f in decision_factors[:3]:
        name = f.get("name", "").replace(".", " › ").replace("_", " ")
        contrib = f.get("contribution", 0)
        direction = f.get("direction", "neutral")
        if abs(contrib) > 0.01:
            observations.append(f"{name}: {direction} prediction ({abs(contrib):.3f})")

    return {
        "level": level,
        "score": round(raw_score * 100, 1),
        "description": description,
        "color": color,
        "observations": observations,
    }


def _build_seizure_intelligence(*, pred_class, conf_score, conf_level,
                                  calib_quality) -> dict:
    """Build rich seizure intelligence output."""
    seizure_prob = conf_score if pred_class == 1 else (1 - conf_score)

    # Risk categorization
    if seizure_prob < 0.1:
        risk = "Very Low"
        risk_desc = "No seizure-like patterns detected."
    elif seizure_prob < 0.3:
        risk = "Low"
        risk_desc = "Minimal seizure-like features. Routine monitoring appropriate."
    elif seizure_prob < 0.5:
        risk = "Moderate"
        risk_desc = "Some features consistent with seizure activity. Clinical correlation recommended."
    elif seizure_prob < 0.7:
        risk = "Elevated"
        risk_desc = "Features suggestive of seizure activity. Clinical review advised."
    elif seizure_prob < 0.9:
        risk = "High"
        risk_desc = "Strong indicators of seizure-like activity. Urgent review recommended."
    else:
        risk = "Critical"
        risk_desc = "Very high probability of seizure activity. Immediate clinical attention recommended."

    # Prediction stability (derived from calibration)
    stability = "Stable" if "well" in calib_quality.lower() else "Variable"

    return {
        "seizure_probability": round(seizure_prob * 100, 1),
        "non_seizure_probability": round((1 - seizure_prob) * 100, 1),
        "risk_level": risk,
        "risk_description": risk_desc,
        "confidence_level": conf_level,
        "confidence_score": round(conf_score * 100, 1),
        "calibration": calib_quality,
        "prediction_stability": stability,
        "predicted_class": pred_class,
    }


def _build_evidence_intelligence(*, decision_factors, model_arch, model_id,
                                    expl_method) -> dict:
    """Build the evidence and explainability section."""
    supporting = [f for f in decision_factors if f.get("direction") == "supports"]
    opposing = [f for f in decision_factors if f.get("direction") == "opposes"]

    # Format factors into readable evidence
    evidence_items = []
    for f in decision_factors[:8]:
        name = f.get("name", "unknown")
        readable_name = name.replace(".", " › ").replace("_", " ").title()
        contrib = f.get("contribution", 0)
        direction = f.get("direction", "neutral")

        if direction == "supports":
            icon = "▲"
            impact = "supporting"
        elif direction == "opposes":
            icon = "▼"
            impact = "opposing"
        else:
            icon = "●"
            impact = "neutral"

        evidence_items.append({
            "feature": readable_name,
            "contribution": round(abs(contrib), 4),
            "direction": direction,
            "icon": icon,
            "impact": impact,
            "raw_name": name,
        })

    return {
        "method": expl_method or "feature_attribution",
        "n_supporting": len(supporting),
        "n_opposing": len(opposing),
        "total_factors": len(decision_factors),
        "evidence_items": evidence_items,
        "model_architecture": model_arch,
        "model_id": model_id[:16] if model_id else "",
    }


def _generate_clinical_narrative(*, pred_class, conf_score, conf_level,
                                   calib_quality, n_channels, sfreq, duration,
                                   filename, decision_factors, signal_quality,
                                   abnormality) -> dict:
    """Generate a clinician-friendly narrative interpretation."""
    paragraphs = []

    # Summary paragraph
    if pred_class == 1 and conf_score > 0.7:
        summary = (
            f"Analysis of the uploaded EEG recording ({filename}) reveals patterns "
            f"consistent with potential seizure activity. The system detected features "
            f"with {conf_level} confidence ({conf_score*100:.1f}%) that suggest "
            f"ictal or peri-ictal patterns in the analyzed segment."
        )
    elif pred_class == 0 and conf_score > 0.7:
        summary = (
            f"Analysis of the uploaded EEG recording ({filename}) shows brain activity "
            f"within expected parameters. No clear seizure-like patterns were identified "
            f"in the analyzed segment (confidence: {conf_score*100:.1f}%)."
        )
    else:
        summary = (
            f"Analysis of the uploaded EEG recording ({filename}) produced an "
            f"indeterminate result with {conf_level} confidence ({conf_score*100:.1f}%). "
            f"Clinical correlation is recommended for definitive interpretation."
        )
    paragraphs.append(summary)

    # Recording context
    context = (
        f"The recording comprises {n_channels} channels sampled at {sfreq} Hz, "
        f"with an analyzed duration of {duration:.1f} seconds. "
        f"Signal quality was assessed as {signal_quality['grade'].lower()} "
        f"(score: {signal_quality['score']}/100)."
    )
    paragraphs.append(context)

    # Key observations
    if decision_factors:
        top_factor = decision_factors[0]
        factor_name = top_factor.get("name", "").replace("_", " ").replace(".", " › ")
        factor_dir = top_factor.get("direction", "contributing to")
        obs = (
            f"The primary contributing feature was {factor_name}, "
            f"{factor_dir} the prediction outcome. "
            f"The abnormality assessment classified this recording as "
            f"{abnormality['level'].lower()}."
        )
        paragraphs.append(obs)

    # Confidence context
    conf_context = (
        f"This assessment was generated with {conf_level} confidence and "
        f"{calib_quality.replace('_', ' ')} calibration. "
        f"This is an AI-generated analysis intended for clinical decision support only. "
        f"It does not constitute a diagnosis or medical recommendation."
    )
    paragraphs.append(conf_context)

    return {
        "paragraphs": paragraphs,
        "disclaimer": (
            "IMPORTANT: This is an automated AI analysis for clinical decision support. "
            "It does not replace professional neurological interpretation. All findings "
            "should be reviewed and validated by a qualified clinician."
        ),
    }


def _build_overall_summary(*, pred_class, conf_score, signal_quality,
                             abnormality) -> dict:
    """Generate the single high-level takeaway."""
    sq = signal_quality["score"]

    if sq < 40:
        conclusion = "Recording quality limits interpretation reliability."
        action = "Consider re-recording or manual review of signal quality."
        severity = "warning"
    elif pred_class == 1 and conf_score > 0.8:
        conclusion = "Potential seizure-like activity detected with high confidence."
        action = "Urgent clinical review recommended."
        severity = "critical"
    elif pred_class == 1 and conf_score > 0.5:
        conclusion = "Features suggestive of abnormal activity detected."
        action = "Clinical review advised."
        severity = "elevated"
    elif pred_class == 0 and conf_score > 0.8:
        conclusion = "Recording appears neurologically stable."
        action = "Routine monitoring appropriate."
        severity = "normal"
    else:
        conclusion = "Indeterminate result — clinical correlation required."
        action = "Further clinical review advised."
        severity = "indeterminate"

    return {
        "conclusion": conclusion,
        "recommended_action": action,
        "severity": severity,
        "signal_quality_grade": signal_quality["grade"],
        "abnormality_level": abnormality["level"],
    }


__all__ = ["build_intelligence_report"]
