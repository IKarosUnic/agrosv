"""AGROSV — Fase 7: monitorización agrícola, sanidad y alertas.

Seis subsistemas:

A. satélite y teledetección   `satellites`, `indices`, `timeseries`, `change`
B. sanidad del cultivo        `crop_health`, `water_stress`
C. plagas y enfermedades      `knowledge`, `pests`
D. riesgo agrícola            `risks`
E. alertas y aviso temprano   `alerts`
F. monitorización integrada   `integration`, `field`

Estado real: no hay escenas satelitales ni series de campo integradas. Los
adaptadores leen archivos locales y los motores declaran la ausencia de datos
en lugar de sustituirla. Ver `docs/phase7/PHASE_7_FINAL_REPORT.md`.
"""
from . import governance

__all__ = ["governance"]
