"""Deterministic simulation/scenario identity generation (V4-P9).

Every simulation artifact has a content-derived identity — a sha256-derived digest of
a canonical payload. Because the digest is a pure function of its inputs it is stable/
deterministic, collision-resistant, versioned, and traceable.

Identities:
  * scenario   : ``scenario+{hash16}``   — a reproducible hypothesis over observed artifacts
  * simulation : ``sim+{hash16}``        — a deterministic evaluation run of a scenario
  * forecast   : ``simfc+{hash16}``      — an explainable projected outcome
  * comparison : ``simcmp+{hash16}``     — a comparison across scenarios
  * risk       : ``simrisk+{hash16}``    — a simulation risk score
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import SIMULATION_IDENTITY_VERSION

_SCENARIO_ID_RE = re.compile(r"^scenario\+[0-9a-f]{16}$")
_SIM_ID_RE = re.compile(r"^sim\+[0-9a-f]{16}$")
_FORECAST_ID_RE = re.compile(r"^simfc\+[0-9a-f]{16}$")
_COMPARISON_ID_RE = re.compile(r"^simcmp\+[0-9a-f]{16}$")
_RISK_ID_RE = re.compile(r"^simrisk\+[0-9a-f]{16}$")


class SimulationIdentityError(ValueError):
    """Raised when simulation/scenario identity minting or validation fails."""


@dataclass(frozen=True)
class ScenarioIdentity:
    id: str
    scenario_type: str
    name: str
    identity_version: str = SIMULATION_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "scenario_type": self.scenario_type, "name": self.name,
                "identity_version": self.identity_version}


def mint_scenario(scenario_type: str, name: str, signature: str) -> ScenarioIdentity:
    if not (scenario_type and name and signature):
        raise SimulationIdentityError("scenario requires type, name, signature")
    payload = {"kind": "scenario", "identity_version": SIMULATION_IDENTITY_VERSION,
               "scenario_type": scenario_type, "name": name, "signature": signature}
    return ScenarioIdentity(id=f"scenario+{hash_obj(payload)}", scenario_type=scenario_type,
                            name=name)


def mint_simulation(scenario_id: str, signature: str) -> str:
    if not (scenario_id and signature):
        raise SimulationIdentityError("simulation requires scenario_id and signature")
    payload = {"kind": "sim", "identity_version": SIMULATION_IDENTITY_VERSION,
               "scenario_id": scenario_id, "signature": signature}
    return f"sim+{hash_obj(payload)}"


def mint_forecast(simulation_id: str, forecast_type: str) -> str:
    if not (simulation_id and forecast_type):
        raise SimulationIdentityError("forecast requires simulation_id and forecast_type")
    payload = {"kind": "simfc", "identity_version": SIMULATION_IDENTITY_VERSION,
               "simulation_id": simulation_id, "forecast_type": forecast_type}
    return f"simfc+{hash_obj(payload)}"


def mint_comparison(scenario_ids: tuple, signature: str) -> str:
    if not (scenario_ids and signature):
        raise SimulationIdentityError("comparison requires scenario_ids and signature")
    payload = {"kind": "simcmp", "identity_version": SIMULATION_IDENTITY_VERSION,
               "scenario_ids": list(scenario_ids), "signature": signature}
    return f"simcmp+{hash_obj(payload)}"


def mint_risk(simulation_id: str, dimension: str) -> str:
    if not (simulation_id and dimension):
        raise SimulationIdentityError("risk requires simulation_id and dimension")
    payload = {"kind": "simrisk", "identity_version": SIMULATION_IDENTITY_VERSION,
               "simulation_id": simulation_id, "dimension": dimension}
    return f"simrisk+{hash_obj(payload)}"


def validate_scenario_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _SCENARIO_ID_RE.match(id_str):
        return False, f"malformed scenario identity {id_str!r}"
    return True, "ok"


def validate_simulation_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _SIM_ID_RE.match(id_str):
        return False, f"malformed simulation identity {id_str!r}"
    return True, "ok"


def validate_forecast_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _FORECAST_ID_RE.match(id_str):
        return False, f"malformed forecast identity {id_str!r}"
    return True, "ok"


def validate_comparison_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _COMPARISON_ID_RE.match(id_str):
        return False, f"malformed comparison identity {id_str!r}"
    return True, "ok"


def validate_risk_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _RISK_ID_RE.match(id_str):
        return False, f"malformed simulation risk identity {id_str!r}"
    return True, "ok"
