# AGROSV — Geospatial Experience (`docs/FRONTEND_GEOSPATIAL_EXPERIENCE.md`)

`AgriculturalMapExperience` (`src/components/maps/AgriculturalMapExperience.tsx`) serves as the central spatial workspace (`/mapa`).

## 1. Integrated Map Layers

1. **Base & Terrain Rasters (Copernicus DEM GLO-30, 30 m DSM):**
   - `hillshade`: `/api/tiles/hillshade/{z}/{x}/{y}.png`
   - `slope`: `/api/tiles/slope/{z}/{x}/{y}.png` (adjustable opacity `15%–100%`)
   - `relief`: `/api/tiles/relief/{z}/{x}/{y}.png` (6-class discrete legend + adjustable opacity)
2. **Territorial Boundaries:**
   - Departments (`adm1`, `/api/territory/departments`): 14 departments with `fitBounds` zoom and summary indicators.
   - Historic Municipalities (`adm2`, `/api/territory/municipalities`): toggleable pre-2023 boundaries explicitly labeled `262 pre-2023`.
3. **OpenStreetMap Layers (bbox-clipped on pan/zoom via `/api/infrastructure/{layer}`):**
   - `water_bodies`, `waterways`, `roads`, `settlements`, `infrastructure`.
4. **Verified Markets Overlay:**
   - Generated from `/api/economics/markets` (WFP + OSM market coordinates).
5. **Satellite Layer Honesty:**
   - Explicitly displays *"Satélite sin escenas: no hay teselas Sentinel/Landsat archivadas en el servidor"* rather than rendering placeholder rasters.

## 2. Location Profile Workflow

Clicking any point on the map (or submitting coordinates via the keyboard-accessible coordinate form) sets a single active marker (replacing prior markers to avoid memory leaks) and opens the integrated **Perfil integrado del punto** drawer querying:
- `/api/engines/environmental` (territory, terrain, SoilGrids 0–30 cm, hydrology, climate)
- `/api/agriculture/suitability` (for the globally selected crop)
- `/api/economics/logistics` (nearest road and nearest verified markets)
