# AGROSV — Frontend Audit (`docs/FRONTEND_AUDIT.md`)

**Audit date:** 2026-11-22  
**Scope:** Complete inspection of `frontend/` and backend API routers (`backend/agrosv/**`) prior to modifying code.

---

## 1. Executive Summary

The existing AGROSV frontend (`frontend/`) is a minimal **Phase 1 geospatial prototype** built with React 18, TypeScript 5.6, Vite 5.4, and MapLibre GL JS 4.7.1. While the backend has grown across Phases 1–8 into a comprehensive 10-router scientific platform (geospatial foundation, science-v1, integrated data catalog, Phase 5 territorial/environmental engines, Phase 6 agricultural intelligence and Nemotron socio-agricultural simulation, Phase 7 monitoring/risks/alerts/field verification, Phase 7 onboarding, and Phase 8 agricultural economics), the frontend still exposes **only 4 Phase 1 endpoints** in a single 459-line file (`frontend/src/App.tsx`).

There is **no routing**, **no design system or dark mode**, **no Phase 2–8 UI**, **no offline persistence**, **no automated frontend tests**, and **no user-profile adaptation** (simple vs. advanced mode). However, the existing Vite + React + TypeScript + MapLibre GL stack is solid, clean, and directly served by FastAPI (`StaticFiles(directory=frontend/dist, html=True)` in `backend/agrosv/api.py`), so preserving and expanding it—rather than introducing a second framework—is the right architectural decision.

---

## 2. Current Frontend Audit (17-Point Checklist)

| # | Dimension | Observed Current State | Assessment |
|---|-----------|------------------------|------------|
| 1 | **Framework & Build** | React `^18.3.1`, TypeScript `^5.6.3`, Vite `^5.4.11` (`vite.config.ts` proxies `/api` to `127.0.0.1:8000`). | **Keep.** Modern, strict (`strict: true`, `noUnusedLocals`), zero bloat. |
| 2 | **Application Architecture** | 3 source files total: `src/main.tsx` (11 lines), `src/styles.css` (86 lines), `src/App.tsx` (459 lines). | Needs modularization into `app/`, `components/`, `modules/`, `services/`, `hooks/`, `stores/`, `types/`, `utils/`. |
| 3 | **Routes & Navigation** | Single screen only; no router, no sidebar, no breadcrumbs, no global search. | Missing all 12 domain views and location-centric workflows. |
| 4 | **Design System** | 7 CSS custom properties in `:root` (`--ink`, `--ink-soft`, `--line`, `--bg`, `--panel`, `--accent`, system-ui font). Light mode only; hardcoded `#fff` and `#eef1ea` in `styles.css` and `App.tsx`. | Needs semantic light/dark design tokens, WCAG 2.2 AA contrast, scientific evidence-class styling, and consistent typography. |
| 5 | **UI Components** | Zero reusable components; all markup inline in `App.tsx`. | Need reusable primitives (`AppShell`, `MetricCard`, `DataStatusBadge`, `SourceAttribution`, `UncertaintyPanel`, `TimeSeriesChart`, `MapView`, etc.). |
| 6 | **Maps & Geospatial** | `maplibre-gl ^4.7.1` with custom raster tiles (`/api/tiles/hillshade`, `slope`, `relief`), GeoJSON departments (`/api/territory/departments`), and bbox-filtered OSM layers (`/api/infrastructure/{layer}`). | **Reuse & extend.** Works well; needs LayerManager (opacity, ordering, legends, metadata, temporal/geo context), location search, municipality toggle, market & observation overlays, and keyboard/point marker cleanup (currently adds unbounded markers on every click). |
| 7 | **Charts & Dashboards** | None. | Needs lightweight, accessible SVG chart system (line, bar, stacked, area, scatter, time-series, comparison) with units, dates, sources, missing-data gaps, and tabular alternatives. |
| 8 | **API Clients** | Raw `fetch()` calls scattered in `App.tsx` (`/api/territory/departments`, `/api/meta`, `/api/infrastructure/{id}`, `/api/topography/elevation`, `/api/soils/point`). No abort controllers, no typing for Phase 2–8, no error/unavailable state differentiation. | Needs centralized typed API client with `AbortController`, caching, timeout/retry, availability tracking, and explicit error classification. |
| 9 | **Auth & Authorization** | **Not implemented** in backend (`api.py` and all Phase 2–8 routers have zero auth middleware or user endpoints). | Do not invent fake security guarantees. Provide client-side **experience mode** (Simple / Farmer vs. Technician / Researcher / Institutional views) persisted in user preferences. |
| 10 | **State Management** | Local `useState` inside `App.tsx`. | Needs lightweight React Context + reducers/hooks for theme, experience profile, selected location (`lat`, `lon`, `territory`), active crop, offline queue, and cached responses. |
| 11 | **Offline Capabilities** | Backend has `GET /api/v1/offline/{department}.zip` and `POST /api/monitoring/notifications/sync`. Frontend has **none** (no service worker, no manifest, no IndexedDB/localStorage drafts). | Needs PWA manifest + Service Worker for app shell & static assets, `localStorage`/IndexedDB cache with timestamps, offline field-observation & budget drafts, and sync queue with explicit stale-data warnings. |
| 12 | **Responsive Behavior** | Single `@media (max-width: 860px)` rule stacking map over side panel (`45vh 1fr`). | Needs mobile-first shell, bottom/drawer mobile nav, 44px+ touch targets, responsive tables/cards, and compact charts. |
| 13 | **Accessibility** | `<div className="map" role="application" aria-label="Mapa de El Salvador" />`, `aria-pressed` on layer chips, `role="group"` on radios. Missing skip-link, focus-visible styles, keyboard map-coordinate entry, chart text alternatives, and non-color status badges. | Target WCAG 2.2 AA across all controls, forms, charts, and modals. |
| 14 | **Existing Tests** | **Frontend:** None (no `test` script in `package.json`). **Backend:** `pytest` suite ran 582 tests: **579 passed**, 3 pre-existing failures in `tests/test_lineage_storage.py`, `tests/test_phase4_performance.py`, and `tests/test_phase7_onboarding.py` (hardcoded Linux paths in `data/manifests/lineage.json` / `data/metadata/raster_catalog.json` and CRLF sha256 mismatch on Windows). | Add Vitest + Testing Library suite for frontend unit, component, accessibility, offline, and integration tests. Preserve all backend tests untouched. |
| 15 | **Backend API Contracts** | 10 routers mounted in `backend/agrosv/api.py`: `/api`, `/api/v1`, `/api/data`, `/api/engines`, `/api/agriculture`, `/api/social`, `/api/socio`, `/api/onboarding`, `/api/monitoring`, `/api/economics`. | Verified live via `FastAPI TestClient`: `/api/health` returns `{"status": "ok", "missing": [], "version": "1.0.0"}`, and all core Phase 1–8 `meta` and catalog endpoints return `200 OK`. |
| 16 | **Phase 5–8 Integrations** | **0%** of Phase 2, 4, 5, 6, 7, and 8 endpoints are wired into the frontend. | Full integration required across all phases, strictly preserving scientific transparency (`evidence_class`, `synthetic`, `limitations`, `null` for gaps). |
| 17 | **Performance Bottlenecks** | Current `npm run build` outputs single JS chunk `959.78 kB` (`gzip: 268.80 kB`) because `maplibre-gl` (~800 kB) is bundled synchronously in `App.tsx`. `App.tsx` also leaks MapLibre `Marker` instances on every click without removing previous markers. | Split `maplibre-gl` into a separate lazy-loaded chunk (`manualChunks` + `React.lazy`), lazy-load route modules, memoize/cancel fetches, and clean up map markers/sources on unmount. |

---

## 3. Observed Backend Data Availability (Real vs. Unavailable)

From live inspection of `backend/agrosv/` and `data/`:

- **Available & Verified:**
  - Territory: 14 departments (`adm1`) & 262 historical pre-2023 municipalities (`adm2`), plus 2023 44-municipality crosswalk (`/api/onboarding/municipalities/*`).
  - Topography: Copernicus DEM GLO-30 (DSM ~30 m), slope, aspect, hillshade, relief classes, TRI/TPI, D8 local watershed & AOI diagnostics.
  - Infrastructure (OSM): roads, waterways, water bodies, settlements, infrastructure, power lines, OSM markets (`osm_markets_slv.json`).
  - Soils: SoilGrids 2.0 (250 m, 0–30 cm modeled predictions: `phh2o`, `soc`, `nitrogen`, `clay`, `sand`, `silt`) + USDA texture derivation.
  - Climate: Two reanalysis point series (2019–2025 daily: `nasa_power_point` and `open_meteo_point`) with ETCCDI indices, monthly climatology, Walter–Lieth seasonality, and 3-month drought percentiles.
  - Agriculture (Phase 6): 22 crops in `CropKnowledgeEngine` (with per-parameter `REF`/`NAC`/`GAP` status), `CropPhenologyEngine`, `CropSuitabilityEngine` (S1/S2/S3/N), `AgriculturalCalendarEngine`, `CropWaterNutrientEngine`, `CropSimulationEngine` (executable `agrosv_water_balance`; AquaCrop-OSPy, PCSE/WOFOST, DSSAT detected/declared as unintegrated).
  - Socio-Agricultural (Phase 6): Nemotron Personas El Salvador agricultural subset + synthetic population/household/adoption/resilience/multiagent/scenario engines (strictly `synthetic: true`).
  - Monitoring & Risks (Phase 7): 6 spectral index formulas + in-memory/local raster index evaluation, pest & disease catalogs (CABI/FAO/OIRSA/CENTA), 6 risk engines, structured alert lifecycle & verification, field observation submission & review workflow (`FLD-*`, in-memory session storage).
  - Economics (Phase 8): CAP 2025 public national/departmental crop aggregates (`cap_2025_public_aggregates.json`), World Bank agricultural land share, WFP/HDX El Salvador food price history (`wfp_food_prices_slv.csv`), WFP + OSM market catalogs, full cost/budget/profitability/break-even/investment/logistics/15 economic scenario engines.
- **Explicitly Unavailable (Must Render Honest Unavailable States):**
  - Sentinel-1/2/Landsat live STAC scene archive (`satellite_scenes_ingested: false`).
  - Groundwater aquifers, piezometric levels, water rights, and river flow gauge calibrations.
  - Official SNET/MARN meteorological station network & gridded climate forecasts/projections.
  - Soil profiles below 0–30 cm (`30-60`, `60-100`, `100-200 cm`), bulk density, CEC, AWC raster, and CENTA national soil map.
  - Official 2023 44-municipality polygon shapefile (`adm2` is pre-2023 historic; 44-municipality data is tabular crosswalk only).
  - Municipal/parcel-level official CAP 2025 production statistics.
  - Persistent database for newly submitted field observations/alerts across server restarts (backend stores them in-memory on `AgriculturalFieldVerificationEngine` / `AgriculturalAlertEngine`).
