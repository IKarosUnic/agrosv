# AGROSV — Frontend API Integration Map (`docs/FRONTEND_API_INTEGRATION_MAP.md`)

Every frontend module is mapped strictly to verified backend endpoints in `backend/agrosv/`. No endpoints are invented or mocked as live production data.

## 1. Phase 1 & 2 — Core Geospatial & Science v1 (`/api`, `/api/v1`)

| Frontend Module | Method & Endpoint | Purpose | Availability / Notes |
|---|---|---|---|
| System / Health | `GET /api/health` | Service status & missing base layers | Live (`200 OK`) |
| Metadata / Provenance | `GET /api/meta`, `GET /api/limitations` | Base layer licenses, CRS, limitations | Live (`200 OK`) |
| Territory Base | `GET /api/territory/departments`, `GET /api/territory/departments/{code}`, `GET /api/territory/municipalities` | GeoJSON boundaries & dept stats | Live (`200 OK`); `adm2` is historic pre-2023 |
| Raster Tiles | `GET /api/tiles/{kind}/{z}/{x}/{y}.png` | `hillshade`, `slope`, `relief` PNG tiles | Live (`z7–z14`) |
| Point Elevation / Soil | `GET /api/topography/elevation`, `GET /api/soils/point` | Fast map-click point query | Live (`200 OK`) |
| OSM Layers | `GET /api/infrastructure/{layer}`, `GET /api/infrastructure/summary` | `roads`, `waterways`, `water_bodies`, `settlements`, `infrastructure`, `power_lines` | Live (`200 OK`), bbox-clipped |
| Science v1 & Offline ZIP | `GET /api/v1/meta`, `/sources`, `/qc`, `/validation/policy`, `/offline/{department}.zip` | Catalog, geometric QC, evidence policy (V0–V4), offline ZIP | Live (`200 OK`) |
| Watershed D8 | `GET /api/v1/hydro/watershed`, `GET /api/v1/hydro/aoi` | Upstream basin GeoJSON & RUSLE LS | Live (`200 OK`), uncalibrated V0 |

## 2. Phase 4 — National Data Catalog (`/api/data`)

| Frontend Module | Method & Endpoint | Purpose | Availability / Notes |
|---|---|---|---|
| Data Explorer | `GET /api/data/catalog` | National dataset inventory & states | Live (`200 OK`) |
| Dataset Detail | `GET /api/data/datasets/{dataset_id}`, `.../lineage` | Assets, reports, derivation chain | Live (`200 OK`) |
| Quality Reports | `GET /api/data/quality/reports` | Geometric/schema QC reports | Live (`200 OK`) |
| Domains & Storage | `GET /api/data/domains`, `GET /api/data/storage` | Domain A–H contracts & SQLite summary | Live (`200 OK`) |

## 3. Phase 5 — Territorial & Environmental Engines (`/api/engines`)

| Frontend Module | Method & Endpoint | Purpose | Availability / Notes |
|---|---|---|---|
| Availability & Coverage | `GET /api/engines/meta`, `/coverage`, `/datasets` | Engine status & explicit unavailable variables | Live (`200 OK`) |
| Territory Search | `GET /api/engines/territory/search?q=&level=` | Resolve dept/historic municipality by ID/name | Live (`200 OK`) |
| Territorial Profile | `GET /api/engines/territorial?lat=&lon=`, `/territory/profile?q=` | Admin ID, terrain, local watershed, dept context | Live (`200 OK`) |
| Terrain Metrics | `GET /api/engines/terrain?lat=&lon=` | Elevation, slope, aspect, TRI, TPI | Live (`200 OK`) |
| Soil Explorer | `GET /api/engines/soil?lat=&lon=`, `/soil/profile` | SoilGrids 0–30 cm, USDA texture, limitations, missing horizons | Live (`200 OK`) |
| Hydrology Explorer | `GET /api/engines/hydrology?lat=&lon=&size_m=` | Surface water proximity, D8 basin, Budyko P−ET0, missing groundwater | Live (`200 OK`) |
| Climate Explorer | `GET /api/engines/climate?lat=&lon=` | Nearest reanalysis point, seasonality, ETCCDI, anomalies, drought %ile | Live (`200 OK`) |
| Integrated Profile | `GET /api/engines/environmental?lat=&lon=` | Unified Phase 5 profile + interaction rules (no composite score) | Live (`200 OK`) |

## 4. Phase 6 — Agricultural Intelligence & Social (`/api/agriculture`, `/api/social`, `/api/socio`)

| Frontend Module | Method & Endpoint | Purpose | Availability / Notes |
|---|---|---|---|
| Crop Catalog & Search | `GET /api/agriculture/crops`, `/crops/{crop_id}`, `/search`, `/audit` | 22 crops with `REF`/`NAC`/`GAP` parameter provenance | Live (`200 OK`) |
| Suitability | `GET /api/agriculture/suitability?crop_id=&lat=&lon=&system=&irrigation_available=` | `S1/S2/S3/N` & explicit limiting factors | Live (`200 OK`) |
| Calendar & Phenology | `GET /api/agriculture/calendar`, `/phenology` | Derived planting windows, GDD stages, stage moisture risks | Live (`200 OK`) |
| Simulation & Water | `GET /api/agriculture/adapters`, `POST /api/agriculture/water`, `POST /api/agriculture/simulate` | FAO-56 water balance (`agrosv_water_balance`) + adapter detection | Live (`200 OK`); external adapters unintegrated |
| Nutrients | `GET /api/agriculture/nutrients` | Crop N/P2O5/K2O demand (not fertilizer prescription) | Live (`200 OK`) |
| Nemotron & Synthetic | `GET /api/social/meta`, `/archetypes`, `/technologies`, `/shocks`, `/nemotron/agricultural` | Nemotron SV agricultural profiles & synthetic definitions | Live (`200 OK`), `synthetic: true` |
| Socio-Ag Scenarios | `GET /api/socio/scenarios`, `POST /api/socio/scenario`, `POST /api/socio/integrate`, `POST /api/socio/decision` | Scenarios A–G & socio-ag integration | Live (`200 OK`); Saltbor integration omitted per spec |

## 5. Phase 7 — Monitoring, Risks, Alerts & Onboarding (`/api/monitoring`, `/api/onboarding`)

| Frontend Module | Method & Endpoint | Purpose | Availability / Notes |
|---|---|---|---|
| Satellite & Indices | `GET /api/monitoring/sources`, `/indices`, `POST /api/monitoring/indices`, `/satellite/search-plan` | Source status, index specs, band arithmetic, STAC plan | Live (`200 OK`); no archived scenes ingested |
| Crop Health & Stress | `POST /api/monitoring/crop-health`, `/vegetation-stress`, `/water-stress`, `/thermal-stress`, `/crop-anomaly` | Transparent anomaly & stress evaluators | Live (`200 OK`), user-supplied / index inputs |
| Pests & Diseases | `GET /api/monitoring/pests`, `/pests/{id}`, `/diseases`, `/diseases/{id}`, `POST /pest-risk`, `/disease-risk` | Catalogs & environmental suitability (not diagnosis) | Live (`200 OK`) |
| Risk Calculators | `POST /api/monitoring/risk`, `/drought`, `/flood-risk`, `/heat-risk`, `/soil-degradation`, `/crop-loss` | `Hazard × Exposure × Vulnerability` & domain risk engines | Live (`200 OK`) |
| Alerts & Verification | `GET /api/monitoring/alerts`, `/alerts/{id}`, `POST /alerts`, `/alerts/{id}/transition`, `/alerts/{id}/verify`, `/early-warning` | Full alert lifecycle, verification events, notifications | Live (`200 OK`), in-memory store per process |
| Field Observations | `GET /api/monitoring/field-observations`, `POST /api/monitoring/field-observations`, `POST .../review` | Community/technician field reports & review workflow | Live (`200 OK`), in-memory store per process |
| Integrated Status | `POST /api/monitoring/status` | Combined monitoring status for `(lat, lon)` | Live (`200 OK`) |
| Crosswalk 2023 | `GET /api/onboarding/municipalities/summary`, `/lookup`, `/districts`, `/sources` | 14 departments / 44 municipalities / 262 districts crosswalk | Live (`200 OK`) |

## 6. Phase 8 — Agricultural Economics (`/api/economics`)

| Frontend Module | Method & Endpoint | Purpose | Availability / Notes |
|---|---|---|---|
| Production & Stats | `GET /api/economics/production/statistics`, `/production/systems`, `POST /production`, `/production/harvest` | CAP 2025, World Bank, 12 production systems, harvest estimates | Live (`200 OK`); municipal CAP unavailable |
| Costs & Budgets | `POST /api/economics/costs/aggregate`, `POST /api/economics/budgets` | Cost breakdown with SV units (`mz`, `ha`, `qq`, `kg`, `t`) | Live (`200 OK`) |
| Markets & Prices | `GET /api/economics/markets`, `GET /api/economics/prices`, `GET /api/economics/prices/history` | WFP/OSM markets & WFP El Salvador price series | Live (`200 OK`) |
| Logistics & Access | `POST /api/economics/logistics`, `POST /api/economics/market-access`, `POST /api/economics/supply-chain` | Nearest markets, OSM road proximity, estimated freight | Live (`200 OK`) |
| Profitability & Break-Even | `POST /api/economics/profitability`, `POST /api/economics/break-even`, `POST /api/economics/gross-margin`, `POST /api/economics/net-margin` | Revenue, margins, break-even price/yield/volume/area, sensitivity | Live (`200 OK`) |
| Economic Scenarios | `GET /api/economics/scenarios`, `POST /api/economics/scenarios/run`, `POST /api/economics/decision-support` | 15 configurable conditional scenarios & trade-off matrix | Live (`200 OK`) |

## 7. Backend Gaps Documented (Not Faked)

1. **Authentication & Role RBAC:** No login/session/JWT endpoints exist in `backend/agrosv/`. Frontend adapts UX via configurable user profile & Simple/Advanced mode without fabricating security guarantees.
2. **Persistent Storage for Field Observations & Alerts:** Backend `AgriculturalFieldVerificationEngine` and `AgriculturalAlertEngine` keep `_observations` and `_alerts` in Python memory dicts. Frontend persists local drafts and syncs to the active backend session, displaying clear status notes.
3. **Live Satellite Raster Tiles / Archive:** No Sentinel-2/Landsat scenes are ingested on disk (`satellite_scenes_ingested: false`). Satellite Explorer displays source status, STAC search planning, spectral index definitions, and interactive band calculation without inventing imagery.
4. **Live Climate Forecasts & Ground Stations:** Not available in backend; frontend never presents reanalysis (`2019–2025`) as real-time station weather or forecasts.
