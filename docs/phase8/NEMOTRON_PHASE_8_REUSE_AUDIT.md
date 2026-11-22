# Auditoría de reutilización de Nemotron en Fase 8

**Módulos auditados:** `backend/agrosv/social/` y `backend/agrosv/economics/household_econ.py`

## 1. Capacidades de Fase 6 verificadas y reutilizadas

| Componente de Fase 6 | Módulo | Uso en Fase 8 |
|---|---|---|
| `NemotronDatasetClient` + corpus agrícola real (363 filas, 14 departamentos) | `agrosv.social.nemotron` | Fuente de perfiles reales `SOURCE_PROFILE` (`from_nemotron_dataset: true`) para hogares económicos |
| `AgriculturalPopulationEngine.generate_from_nemotron` | `agrosv.social.population` | Población agrícola sintética anclada a filas reales de Nemotron |
| `AgriculturalHouseholdEngine.compose` | `agrosv.social.household` | Base `HOUSEHOLD_STATE` reutilizada por `AgriculturalHouseholdEconomyEngine`, `AgriculturalResourceAllocationEngine` y `AgriculturalLivelihoodEngine` |
| `TechnologyAdoptionEngine` (`TECHNOLOGIES`, barreras duras) | `agrosv.social.adoption` | Base reutilizada por `AgriculturalTechnologyEconomicsEngine` |
| `FarmerBehaviorEngine` (MAUT + restricciones duras) | `agrosv.social.behavior` | Base reutilizada por `AgriculturalEconomicBehaviorEngine` |
| `social.governance` (`make_record`, `check_separation`) | `agrosv.social.governance` | Separación estricta de capas en registros `SIMULATION_HISTORY` |
| `saltbor_adapter` (etapa E7) | `agrosv.social.saltbor_adapter` | Frontera HTTP/JSON independiente con `IKarosUnic/sv-people`; no fusionada ni importada en Fase 8 |

## 2. Qué NO se duplicó

- No se reimplementó la generación de población ni de perfiles `SOURCE_PROFILE`.
- No se duplicó `HOUSEHOLD_STATE`, `TechnologyAdoptionEngine` ni el motor MAUT de `FarmerBehaviorEngine`.
- No se fusionó el repositorio `IKarosUnic/sv-people` (Saltbor) ni se comparte base de datos SQLite.

## 3. Reglas de separación preservadas

1. Todo registro de economía de hogar lleva `synthetic: true`.
2. Ninguna decisión sintética se presenta como comportamiento observado de productores salvadoreños (`represents_observed_farmer_behavior: false`).
3. Los ingresos o consumos no aportados por el usuario permanecen en `null`.
