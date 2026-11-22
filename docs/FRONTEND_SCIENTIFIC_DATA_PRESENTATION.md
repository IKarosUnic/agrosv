# AGROSV — Scientific Data Presentation (`docs/FRONTEND_SCIENTIFIC_DATA_PRESENTATION.md`)

Every module enforces strict epistemic separation so users never confuse measurements with estimates or synthetic simulations:

1. **Evidence Classification (`EvidenceBadge`):**
   - `observed` / `official_statistic`: ground or institutional data (e.g., CAP 2025, WFP food prices, OSM features).
   - `reanalysis`: Open-Meteo and NASA POWER 2019–2025 daily point series (explicitly labeled as non-station reanalysis with distance in km).
   - `modeled_prediction`: Copernicus DEM GLO-30 and SoilGrids 2.0 250 m predictions (explicitly labeled as not laboratory soil tests).
   - `derived`: D8 local watersheds, Budyko runoff, derived agricultural calendars (labeled `no oficial`).
   - `field_observation`: community/technician submissions (`verified_scientific_record: false`).
   - `synthetic_scenario` / `simulated`: Nemotron Personas El Salvador profiles and Phase 8 economic scenarios (explicitly labeled *"Simulación sintética — no es un hogar real observado ni encuestado"*).
   - `unavailable`: missing horizons below 30 cm, groundwater aquifers, satellite archives, municipal CAP statistics, forecasts.
2. **Null & Gap Handling:** `fmtNum` and `fmtUsd` render `No disponible` for `null`/`undefined`/`NaN`. Line charts break segments on `null` rather than fabricating interpolated curves.
3. **Adaptive Complexity:** Simple (Farmer) mode collapses dense `UncertaintyPanel` disclosures by default while keeping critical warnings visible; Advanced (Technician / Researcher / Institutional) mode exposes full provenance, raw parameter gaps (`GAP`), and CSV/JSON exports.
