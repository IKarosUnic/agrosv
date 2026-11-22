# AGROSV — Frontend Architecture (`docs/FRONTEND_ARCHITECTURE.md`)

## 1. Architectural Principles

1. **Single Integrated Product:** Preserve the existing React 18 + TypeScript + Vite + MapLibre GL JS foundation and upgrade it into a unified scientific geospatial platform rather than creating a second framework or disjointed sub-apps.
2. **Backend-Authoritative Science:** All agronomic, hydrological, climate, monitoring, risk, socio-agricultural, and economic calculations run in the FastAPI backend engines (`/api`, `/api/v1`, `/api/data`, `/api/engines`, `/api/agriculture`, `/api/social`, `/api/socio`, `/api/onboarding`, `/api/monitoring`, `/api/economics`). The frontend performs only unit formatting, display transformations, client-side filtering, and draft persistence.
3. **Epistemic Transparency First:** Every data point or result surfaces its `evidence_class` (`observed`, `official_statistic`, `reanalysis`, `satellite_derived`, `modeled_prediction`, `derived`, `forecast`, `synthetic_scenario`, `field_observation`, `unavailable`), `sources`, observation/reference dates, units, `limitations`, and uncertainty. Synthetic Nemotron outputs are always visibly separated and labeled.
4. **Resilient Degradation & Offline-First:** Every module handles `503` / `404` / offline states gracefully without crashing or fabricating fallback numbers. Field observation drafts, cost budgets, and location snapshots persist locally with explicit sync/stale timestamps.

---

## 2. Directory Structure

```text
frontend/
  public/
    manifest.webmanifest       # PWA metadata
    sw.js                      # Offline app-shell & static asset Service Worker
  src/
    app/
      routes.ts                # Navigation manifest, route metadata, mode visibility
      AppShell.tsx             # Responsive sidebar, mobile drawer, header, breadcrumbs, help
    components/
      accessibility/           # SkipLink, LiveRegion, AccessibleTableToggle
      charts/                  # SvgLineChart, SvgBarChart, SvgScatterChart, ChartFrame
      data-status/             # EvidenceBadge, DataStatusBanner, SourceAttribution, UncertaintyPanel, EmptyState, ErrorState, LoadingState
      dashboard/               # MetricCard, KpiGrid
      maps/                    # AgriculturalMapExperience, LayerManager, MapLegend, LocationProfileDrawer
      navigation/              # GlobalSearchModal, ProfileModeSwitcher, ThemeSwitcher, OfflineIndicator
    modules/
      home/                    # Inicio (National + selected location overview, quick workflows)
      map/                     # Mapa agrícola (Full-viewport central geospatial workspace)
      territory/               # Territorio y recursos (Phase 5: Territorial, Soil, Hydrology, Climate, Environmental)
      crops/                   # Cultivos (Phase 6: Catalog, Details, Suitability, Simulation)
      calendar/                # Calendario agrícola (Phase 6: Planting windows, Phenology, Stage risks)
      monitoring/              # Monitoreo (Phase 7: Satellites/Indices, Crop Health, Pests/Diseases, Field Observations)
      risks/                   # Riesgos y alertas (Phase 7: Risk calculators, Alert center & verification)
      economics/               # Producción, Costos, Mercados, Rentabilidad, Escenarios (Phase 8)
      research/                # Datos e investigación (Phases 2, 4, 6-social, 7-onboarding: Catalog, QC, Offline ZIPs, Nemotron)
    services/
      api/
        client.ts              # Typed fetch wrapper (AbortController, timeout, caching, structured errors)
        endpoints.ts           # Typed methods mapped to backend routers
      offline/
        storage.ts             # Versioned localStorage / IndexedDB wrapper, draft queue, cached location profiles
        sync.ts                # Online/offline listener & queue synchronization
    stores/
      AppContext.tsx           # Global state: theme, experienceMode (simple/advanced), selectedLocation, selectedCrop, onlineStatus
    types/
      api.ts                   # Strict TypeScript contracts for Phase 1–8 responses
    utils/
      format.ts                # Number, coordinate, date, and Salvadoran unit formatting (mz, qq, ha, t, USD)
      csv.ts                   # Client-side CSV/JSON export for researcher mode
    styles/
      tokens.css               # Centralized light & dark theme CSS custom properties
      global.css               # Base layout, typography, accessibility focus rings, responsive utilities
    main.tsx
    App.tsx                    # Lazy-loaded route host inside AppContext + AppShell
```

---

## 3. State Management & Data Flow

1. **Global AppContext (`src/stores/AppContext.tsx`):**
   - `theme`: `"light" | "dark" | "system"` (persisted in `localStorage`, applied via `data-theme` attribute on `<html>`, synchronized with MapLibre background and SVG chart colors).
   - `experienceMode`: `"farmer" | "technician" | "researcher" | "institutional"` + `simpleMode: boolean` toggle. Adapts language complexity, collapses dense technical provenance panels by default in Farmer mode, and surfaces raw parameters/exports/Nemotron research tools in Researcher/Technician modes.
   - `selectedLocation`: `{ lat: number; lon: number; label?: string; departmentCode?: string; departmentName?: string; municipalityName?: string }`. Persisted across route transitions so a user can pick a location on the map or global search and seamlessly inspect Soil, Suitability, Calendar, Risk, Logistics, and Profitability for that exact point.
   - `selectedCropId`: Shared active crop across Suitability, Calendar, Simulation, Cost Calculator, and Prices.
2. **API Client & Cache Layer (`src/services/api/client.ts`):**
   - In-memory TTL cache for static/slow-changing catalogs (`/api/meta`, `/api/agriculture/crops`, `/api/economics/markets`, `/api/engines/datasets`).
   - Persistent offline snapshot fallback in `localStorage` tagged with `cachedAt` ISO timestamp so offline users see cached values clearly marked *"Caché local sin conexión — última sincronización: …"*.
   - Request cancellation via `AbortSignal` on location or filter changes.

---

## 4. Code Splitting & Bundle Strategy

- **Vite `manualChunks`:** Separate `maplibre-gl` into its own vendor chunk (`vendor-maplibre`) and React into `vendor-react`, plus route-level `React.lazy()` + `Suspense` for all 12 domain views.
- **Lazy Map Initialization:** `AgriculturalMapExperience` is only loaded on `/` (mini preview or trigger) and `/mapa` (full interactive map), eliminating the 960 kB upfront single-bundle warning for non-map entry routes.
