# AGROSV — Offline Architecture (`docs/FRONTEND_OFFLINE_ARCHITECTURE.md`)

## 1. Capabilities Implemented

1. **PWA App Shell (`public/manifest.webmanifest`, `public/sw.js`):**
   - Registered in production builds (`src/main.tsx`).
   - Caches static shell (`/`, `/index.html`, `/assets/*`) for offline load while excluding `/api/` tile collections and mutable endpoints from blind SW caching.
2. **Selective API Response Cache (`src/services/api/client.ts`, `src/services/offline/storage.ts`):**
   - Stores up to 45 recent GET JSON payloads in `localStorage` (`agrosv_v1_api_cache`) with ISO `cachedAt` timestamps.
   - On network failure, serves cached responses with `fromCache: true` and displays `CacheNotice` showing the exact last synchronization UTC timestamp.
3. **Offline Field Observations & Sync (`src/services/offline/sync.ts`):**
   - Producers/technicians can save drafts (`draft`) or queue observations (`queued`) when offline.
   - Automatically attempts synchronization on the browser `online` event or via the manual **Sincronizar cola** button.
   - Detects and surfaces duplicate-record warnings (`conflict`) returned by `/api/monitoring/field-observations`.
4. **Offline Production Budgets & Territorial Packages:**
   - `ProductionCostsPage` saves budgets locally (`agrosv_v1_cost_budgets`).
   - `ResearchDataPage` provides direct links to backend-generated `/api/v1/offline/{department}.zip` packages.

## 2. Explicit Limitations

- Does **not** attempt to cache national GeoTIFFs, MapLibre raster tile pyramids, or satellite scenes locally.
- Interactive calculations requiring backend engines (`POST /api/agriculture/simulate`, `/api/economics/profitability`, etc.) clearly report offline unavailability instead of faking backend logic in the browser.
