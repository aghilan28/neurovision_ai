"""Cross-cutting, multi-module test suite (test-only sink).

This package is permitted to import **every** module (it verifies that everyone
else obeys the rules). It is never imported by production code.
"""
