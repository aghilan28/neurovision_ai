"""``scripts/`` — operational orchestration entry points (V1).

Scripts compose modules across layers for repeatable operational tasks. They are
the only place permitted to wire ``ml`` and ``evaluation`` together, because the
import DAG forbids ``ml`` from importing ``evaluation`` (NR-8): the cross-layer
orchestration belongs here, above both. Production modules never import scripts.
"""
