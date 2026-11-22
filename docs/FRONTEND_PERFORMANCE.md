# AGROSV — Performance Report (`docs/FRONTEND_PERFORMANCE.md`)

## 1. Bundle & Code-Splitting Measurements (`vite build`)

- **Baseline (Phase 1 `App.tsx`):** Single JS chunk `959.78 kB` (`268.80 kB` gzip) with Vite >900 kB chunk warning.
- **Current Production Build (`npm run build`, 63 modules, 3.70s):** Zero chunk-size warnings:
  - `dist/index.html`: `0.78 kB` (`0.45 kB` gzip)
  - `dist/assets/index-*.css`: `13.15 kB` (`3.40 kB` gzip)
  - `dist/assets/index-*.js` (App shell + Home): `53.26 kB` (`17.58 kB` gzip)
  - `dist/assets/vendor-react-*.js`: `141.00 kB` (`45.31 kB` gzip)
  - Route lazy chunks: `CalendarPage` (`4.17 kB`), `ResearchDataPage` (`4.49 kB`), `RisksAlertsPage` (`6.39 kB`), `ScenariosPage` (`6.55 kB`), `MarketsPricesPage` (`6.79 kB`), `ProfitabilityPage` (`6.95 kB`), `ProductionCostsPage` (`12.09 kB`), `CropsPage` (`14.02 kB`), `MonitoringPage` (`14.23 kB`), `TerritoryPage` (`14.74 kB`), `MapPage` (`17.68 kB`).
  - `dist/assets/vendor-maplibre-*.js` (`801.65 kB` / `217.61 kB` gzip) + `MapPage-*.css` (`65.48 kB` / `9.22 kB` gzip): **deferred** until the user navigates to `/mapa`.

## 2. Runtime & Memory Optimizations

- **Request Cancellation:** Every page effect passes `AbortController.signal` to `apiGet`/`apiPost`, cancelling stale fetches on rapid location or tab changes.
- **TTL & Bounded Offline Cache:** Catalogs (`/api/agriculture/crops`, `/api/territory/departments`, `/api/meta`, `/api/economics/markets`) use in-memory TTL caching (5 min to 1 h) and bounded `localStorage` persistence (max 45 entries).
- **MapLibre Memory Hygiene:** Fixed the Phase 1 marker leak by maintaining a single `markerRef` instance (removing prior markers on click and on component unmount) and clearing OSM GeoJSON sources when layers are toggled off.
- **Zero Heavy Chart/UI Libraries:** Custom lightweight SVG charts (`Charts.tsx`, `5.21 kB`) and inline SVG icons avoid shipping large charting or icon bundles.

## 3. Unmeasured Runtime Metrics

- Browser Lighthouse LCP/INP/CLS and live memory heap profiling were not measured in a headless Chromium runtime in this session.
