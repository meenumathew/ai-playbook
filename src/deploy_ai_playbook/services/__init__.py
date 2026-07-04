"""Service-layer modules for the deploy CLI.

Each service computes a structured result. The Typer command layer (`cli.py`)
calls a service and renders. This mirrors the existing `DoctorService` pattern
in `doctor.py` and keeps `cli.py` thin.
"""
