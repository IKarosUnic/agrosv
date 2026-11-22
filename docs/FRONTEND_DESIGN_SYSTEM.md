# AGROSV — Design System (`docs/FRONTEND_DESIGN_SYSTEM.md`)

## 1. Visual Identity

AGROSV uses a scientific geospatial aesthetic tailored to Salvadoran agriculture:
- **Forest Green (`--accent-primary`)**: `#1f5c37` (Light) / `#4fb075` (Dark) for primary actions and active navigation.
- **Natural Greens & Earth Tones (`--domain-vegetation`, `--domain-soil`)**: vegetation health and soil properties.
- **Water Blue (`--domain-water`)**: `#175c85` (Light) / `#63b5e3` (Dark) for hydrology, rainfall, and ET0 charts.
- **Semantic Status Tokens**: `--status-ok`, `--status-warn`, `--status-crit`, `--status-info`, `--status-unavailable`, `--status-synthetic`.

## 2. Light & Dark Themes

Defined centrally in [tokens.css](file:///c:/GIT%20HUB/agrosv/frontend/src/styles/tokens.css) and switched via `data-theme="light" | "dark"` on `<html>` by `AppProvider`:
- Respects `prefers-color-scheme` when set to `system`.
- Persists user choice in `localStorage` (`agrosv_v1_preferences`).
- Adapts MapLibre GL canvas background (`--map-bg`), department boundary line color, SVG charts, tables, callouts, and modals.

## 3. Typography & Numeric Discipline

- System UI sans-serif stack (`--font-sans`) for fast zero-network load on low-resource Android devices.
- `font-variant-numeric: tabular-nums` on all scientific metrics, coordinates, dates, and financial tables.
- Monospace (`--font-mono`) for dataset identifiers, codes, and formulas.
