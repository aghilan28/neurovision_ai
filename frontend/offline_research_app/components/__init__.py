"""``frontend/offline_research_app/components`` — reusable view-model builders (V1-P8).

Small, pure builders that turn registered-artifact data into ``Section`` view-models
(key-value panels, tables, badge rows, text). No domain logic, no recomputation.
"""

from __future__ import annotations

from .components import kv_panel, table, badges, text, metric_row

__all__ = ["kv_panel", "table", "badges", "text", "metric_row"]
