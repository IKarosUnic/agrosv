# AGROSV — Frontend Final Report (`docs/FRONTEND_FINAL_REPORT.md`)

**Completion Date:** 2026-11-22  
**Status:** Complete across Stages 1–11.

---

## 1. Existing Frontend Features Reused & Preserved

- **Core Stack:** Kept React 18, TypeScript 5.6 (strict mode), Vite 5.4, and MapLibre GL JS 4.7.1, served from FastAPI `StaticFiles(directory=frontend/dist, html=True)`.
- **Phase 1 Geospatial Layers:** Preserved `/api/tiles/hillshade`, `/api/tiles/slope`, `/api/tiles/relief`, `/api/territory/departments`, `/api/territory/departments/{code}`, `/api/infrastructure/{layer}`, and `/api/meta`, while fixing marker leaks and adding theme/opacity/keyboard controls.

## 2. New Modules Implemented

1. **Design System & Primitives:** Centralized light/dark tokens (`src/styles/tokens.css`, `src/styles/global.css`), `AppShell`, `GlobalSearchModal`, `EvidenceBadge`, `DataStatusBadge`, `SourceAttribution`, `UncertaintyPanel`, `MetricCard`, `ChartFrame`, `SvgBarChart`, `SvgLineChart`.
2. **Home Dashboard (`HomeDashboard.tsx`):** Integrated El Salvador overview, department selector, active location environmental summary, active session alerts, CAP 2025 + World Bank stats, and guided workflows.
3. **Geospatial Workspace (`AgriculturalMapExperience.tsx`):** Multi-category Layer Manager (DEM overlays with opacity, OSM vectors, historic pre-2023 municipalities, WFP/OSM markets), keyboard coordinate input, and integrated Phase 5–8 location profile drawer.
4. **Phase 5 (`TerritoryPage.tsx`):** Integrated Environmental Profile, Territorial & Terrain, Soil (0–30 cm + missing horizons), Hydrology (OSM proximity vs. D8 watershed vs. Budyko P−ET0 vs. unavailable groundwater), and Climate (2019–2025 reanalysis, seasonality charts, ETCCDI, drought percentiles).
5. **Phase 6 (`CropsPage.tsx`, `CalendarPage.tsx`):** 22-crop catalog with `REF`/`NAC`/`GAP` status, detail views, S1–N suitability evaluator, derived planting windows & GDD phenology calendar, and FAO-56 water balance simulation + unintegrated adapter status table.
6. **Phase 7 (`MonitoringPage.tsx`, `RisksAlertsPage.tsx`):** Satellite source/index status & band calculator, crop health evaluator, CABI/FAO/OIRSA/CENTA pest & disease catalogs, mobile-first field observation form with offline drafts & sync, drought/flood risk evaluators, and alert lifecycle & verification center.
7. **Phase 8 (`ProductionCostsPage.tsx`, `MarketsPricesPage.tsx`, `ProfitabilityPage.tsx`, `ScenariosPage.tsx`):** CAP 2025 production stats, Salvadoran-unit cost calculator (`mz`, `ha`, `qq`, `kg`, `t`, `USD`) with local budget storage & CSV export, WFP price explorer & time-series charts, WFP/OSM market logistics, profitability & break-even sensitivity analysis, 15 configurable economic scenarios, and Nemotron socio-agricultural exploration.
8. **Science & Data (`ResearchDataPage.tsx`):** Phase 4 data catalog, Phase 2 V0–V4 validation status, 2023 44-municipality crosswalk lookup, and offline department `.zip` downloads.

## 3. Backend Connectivity & Explicit Gaps

- **Connected to Live Backend Endpoints:** All 12 navigation modules call live FastAPI endpoints under `/api`, `/api/v1`, `/api/data`, `/api/engines`, `/api/agriculture`, `/api/social`, `/api/socio`, `/api/onboarding`, `/api/monitoring`, and `/api/economics`.
- **Documented Missing Backend Support (Rendered Honestly as Unavailable):**
  - Authentication/RBAC (handled as client-side experience mode without faking security).
  - Archived Sentinel/Landsat scene rasters (`satellite_scenes_ingested: false`).
  - Groundwater aquifers, piezometric levels, SNET/MARN ground stations, climate forecasts, soil profiles >30 cm, and municipal CAP 2025 statistics.
  - Persistent database for newly submitted field observations/alerts across backend process restarts (backend stores them in-memory).
- **Development/Test Mocks:** Production client (`src/services/api/client.ts`) contains **zero** hardcoded demo data; API mocks are strictly isolated inside `src/test/*.test.*`.

## 4. Offline, Accessibility, Performance & Testing Summary

- **Offline:** PWA manifest + Service Worker (`public/sw.js`), bounded `localStorage` API cache with `cachedAt` stale notices, offline field observation drafts + sync conflict detection, local cost budgets, and backend `.zip` territorial packages.
- **Accessibility:** Semantic landmarks, skip-link, visible focus rings, `Ctrl+K` global search, keyboard coordinate query, non-color-only status badges, 44px mobile touch targets, and accessible chart-to-table toggle.
- **Performance:** Code-split routes + deferred `vendor-maplibre` (`801.65 kB`), keeping core shell chunk at `53.26 kB` (`17.58 kB` gzip) with zero Vite chunk warnings.
- **Automated Tests:** Frontend Vitest suite `5 files / 17 tests passed`; `tsc -b && vite build` passed cleanly; FastAPI `TestClient` verified `200 OK` on `/` and all Phase 1–8 sample endpoints; existing backend `pytest` suite remains untouched (`579 passed, 3 pre-existing Windows manifest/path failures`).

## 5. Known Limitations & Remaining Frontend Tasks

- Headless browser E2E (Playwright) and live Lighthouse/axe-core contrast scans were not executed in this environment and are recommended when running in a browser CI runner.
- `AgriculturalMapExperience` relies on MapLibre WebGL rendering, so full interactive map canvas tests require WebGL-enabled Playwright/Chromium rather than jsdom.
