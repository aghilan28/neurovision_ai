"""Declarative default clinical knowledge (DATA, not code).

Knowledge must never be hidden in code (a V2-P4 principle). This module is a
declarative seed — plain data — that the governed ``KnowledgeService`` loads into
the versioned, audited, lineage-tracked registries. Editing knowledge means editing
this data + re-seeding, never changing logic. The content is ACNS-aligned EEG
terminology + platform concepts; it asserts no diagnosis or decision.
"""

from __future__ import annotations

KNOWLEDGE_SOURCE = {"name": "ACNS-ICU-EEG-and-platform", "version": "1.0.0"}

# Taxonomy: (category, name, parent_name|None). Roots have parent None.
TAXONOMY = [
    ("clinical", "Clinical Concepts", None),
    ("eeg", "EEG Concepts", None),
    ("finding", "Finding Concepts", None),
    ("interpretation", "Interpretation Concepts", None),
    ("knowledge", "Knowledge Concepts", None),
    ("relationship", "Relationship Concepts", None),
    ("eeg", "Periodic Patterns", "EEG Concepts"),
    ("eeg", "Rhythmic Patterns", "EEG Concepts"),
    ("eeg", "Background", "EEG Concepts"),
    ("eeg", "Artifacts", "EEG Concepts"),
    ("clinical", "Ictal-Interictal Continuum", "Clinical Concepts"),
    ("knowledge", "Uncertainty Concepts", "Knowledge Concepts"),
]

# Terms: (term, definition, source). Deidentified, descriptive only.
TERMS = [
    ("IIC", "Ictal-interictal continuum: patterns between clearly ictal and interictal.", "ACNS"),
    ("LPD", "Lateralized periodic discharges.", "ACNS"),
    ("GPD", "Generalized periodic discharges.", "ACNS"),
    ("LRDA", "Lateralized rhythmic delta activity.", "ACNS"),
    ("GRDA", "Generalized rhythmic delta activity.", "ACNS"),
    ("Seizure", "Electrographic seizure pattern.", "ACNS"),
    ("Background Activity", "Ongoing background EEG activity.", "ACNS"),
    ("Artifact", "Non-cerebral signal contaminating the EEG.", "ACNS"),
    ("Calibration", "Agreement between predicted confidence and observed accuracy.", "platform"),
    ("Coverage", "Empirical coverage of conformal prediction sets vs. target.", "platform"),
    ("Risk", "Recorded per-window risk score derived from calibrated uncertainty.", "platform"),
    ("Finding", "A structured clinical observation linked to evidence.", "platform"),
    ("Interpretation", "A structured interpretation referencing evidence + concepts.", "platform"),
]

# Concepts: (name, description, [term names], (category, taxon name)|None).
CONCEPTS = [
    ("Ictal-Interictal Continuum", "Family of periodic/rhythmic patterns on the IIC.",
     ["IIC", "LPD", "GPD", "LRDA", "GRDA"], ("clinical", "Ictal-Interictal Continuum")),
    ("Lateralized Periodic Discharges", "Periodic discharges with a lateralized field.",
     ["LPD"], ("eeg", "Periodic Patterns")),
    ("Generalized Periodic Discharges", "Periodic discharges with a generalized field.",
     ["GPD"], ("eeg", "Periodic Patterns")),
    ("Rhythmic Delta Activity", "Lateralized/generalized rhythmic delta activity.",
     ["LRDA", "GRDA"], ("eeg", "Rhythmic Patterns")),
    ("Electrographic Seizure", "An electrographic seizure pattern.",
     ["Seizure"], ("eeg", "EEG Concepts")),
    ("Background Activity", "Ongoing background EEG.", ["Background Activity"], ("eeg", "Background")),
    ("Recording Artifact", "Non-cerebral contamination.", ["Artifact"], ("eeg", "Artifacts")),
    ("Model Calibration", "Calibrated confidence concept.",
     ["Calibration"], ("knowledge", "Uncertainty Concepts")),
    ("Conformal Coverage", "Coverage guarantee concept.",
     ["Coverage"], ("knowledge", "Uncertainty Concepts")),
    ("Risk Estimate", "Recorded risk concept.", ["Risk"], ("knowledge", "Uncertainty Concepts")),
    ("Clinical Finding", "The finding entity concept.", ["Finding"], ("finding", "Finding Concepts")),
    ("Clinical Interpretation", "The interpretation entity concept.",
     ["Interpretation"], ("interpretation", "Interpretation Concepts")),
]
