# AGROSV — Component Library (`docs/FRONTEND_COMPONENT_LIBRARY.md`)

Implemented reusable components under `frontend/src/`:

- **Layout & Navigation:**
  - `AppShell` (`src/app/AppShell.tsx`): responsive desktop sidebar, mobile slide-over drawer, breadcrumbs, global search trigger (`Ctrl+K`), profile selector, simple/advanced toggle, theme toggle, contextual help dialog.
  - `GlobalSearchModal` (`src/components/navigation/GlobalSearchModal.tsx`): unified search across departments, territorial index, crops, markets, pests, and map layers.
  - `PageHeader` (`src/components/dashboard/MetricCard.tsx`): consistent module title, subtitle, and action slot.
- **Scientific & Data Status Primitives (`src/components/data-status/DataStatus.tsx`):**
  - `EvidenceBadge`: renders non-color-only badge (icon + text) for `observed`, `official_statistic`, `reanalysis`, `modeled_prediction`, `derived`, `field_observation`, `synthetic`, `unavailable`.
  - `DataStatusBadge`: generic accessible status pill (`ok`, `warn`, `crit`, `info`, `unavailable`, `synthetic`).
  - `SourceAttribution`: displays dataset sources, date, and native spatial resolution.
  - `UncertaintyPanel`: collapsible disclosure for assumptions, limitations, and uncertainty notes.
  - `CacheNotice`, `LoadingState`, `EmptyState`, `ErrorState`.
- **Dashboard & Visualization:**
  - `MetricCard` (`src/components/dashboard/MetricCard.tsx`).
  - `ChartFrame`, `SvgBarChart`, `SvgLineChart` (`src/components/charts/Charts.tsx`): responsive SVG charts with explicit units, date ranges, sources, missing-data gap handling (`null` breaks line segments rather than interpolating), and a one-click **Tabla accesible** toggle.
- **Geospatial:**
  - `AgriculturalMapExperience` (`src/components/maps/AgriculturalMapExperience.tsx`): MapLibre GL map, layer manager, opacity slider, relief legend, coordinate entry form, and integrated Phase 5–8 location profile drawer.
- **Iconography (`src/components/icons/Icons.tsx`):** lightweight inline SVG stroke icons (`aria-hidden="true"`).
