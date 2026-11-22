# AGROSV — Testing Report (`docs/FRONTEND_TESTING_REPORT.md`)

## 1. Frontend Automated Test Suite (`npm test` — Vitest + Testing Library)

Executed after the final code edit:

- **Test Files:** `5 passed (5)`
- **Tests:** `17 passed (17)` (0 skipped, 0 relaxed assertions)
- **Breakdown:**
  1. `src/test/formatAndUnits.test.ts` (4 tests): Salvadoran area (`1 mz = 0.70 ha`) and mass (`1 qq = 46 kg`) conversions, explicit `No disponible` formatting for null/NaN, and evidence class badge mappings.
  2. `src/test/offlineAndSync.test.ts` (3 tests): offline `localStorage` fallback with `cachedAt` timestamp on network error, queued field observation sync + duplicate conflict detection (`FLD-0`), and local budget persistence.
  3. `src/test/navigationAndAccessibility.test.tsx` (3 tests): skip-link, semantic landmarks, breadcrumbs, light/dark theme attribute toggle, role profile switching, sidebar navigation, chart accessible table toggle, and non-color-only status badges.
  4. `src/test/modulesIntegration.test.tsx` (4 tests): `HomeDashboard` metrics + CAP 2025 table, `CropsPage` S1–N suitability evaluation, `ProfitabilityPage` partial-cost warning + break-even outputs, and `ScenariosPage` strict Nemotron synthetic labeling.
  5. `src/test/monitoringTerritoryMarkets.test.tsx` (3 tests): `TerritoryPage` unavailable groundwater & non-station climate notices, `MonitoringPage` offline draft persistence + `RisksAlertsPage` non-official alert notice, and `MarketsPricesPage` WFP observation dates + `wholesale` badge.

## 2. TypeScript & Production Build (`npm run build`)

- `tsc -b && vite build` exited with code `0` (`63 modules transformed`, `0` TypeScript errors, `0` bundle size warnings).

## 3. FastAPI Static Serving & Live Endpoint Verification

- `GET /`, `GET /manifest.webmanifest`, and `GET /sw.js` served via `agrosv.api:app` returned `200 OK`.
- Live `TestClient` probes against `/api/health`, `/api/meta`, `/api/v1/meta`, `/api/engines/meta`, `/api/engines/datasets`, `/api/engines/environmental`, `/api/agriculture/crops`, `/api/agriculture/suitability`, `/api/monitoring/meta`, `/api/monitoring/alerts`, `/api/monitoring/field-observations`, `/api/economics/production/statistics`, `/api/economics/markets`, `/api/economics/prices`, `/api/social/nemotron/agricultural`, `/api/onboarding/meta`, and `/api/data/catalog` all returned `200 OK`.

## 4. Backend `pytest` Baseline

- Ran `.venv\Scripts\python.exe -m pytest -q` (no backend files were modified): **579 passed, 3 failed** (pre-existing Windows environment failures in `tests/test_lineage_storage.py::test_grafo_real_verificado`, `tests/test_phase4_performance.py::test_perfil_de_rasters_gestionados_por_cabecera` due to Linux paths `\workspace\chats\...` in JSON manifests, and `tests/test_phase7_onboarding.py::test_crosswalk_provenance_checksum_matches_file` due to sha256 mismatch on Windows).
