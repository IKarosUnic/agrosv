# AGROSV — Accessibility Report (`docs/FRONTEND_ACCESSIBILITY.md`)

## 1. WCAG 2.2 AA Measures Implemented

- **Semantic Landmarks & Skip Navigation:**
  - `AppShell` provides `<a href="#main-content" class="skip-link">`, `<aside>` navigation landmark, `<header>` topbar, `<nav aria-label="Ruta actual">` breadcrumbs, and `<main id="main-content" tabindex="-1">`.
- **Keyboard Operability & Focus Visibility:**
  - Global `:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px; }` across all buttons, inputs, selects, tabs, and links.
  - Global Search opens via `Ctrl+K` / `Cmd+K` and closes via `Esc` (`role="dialog"`, `aria-modal="true"`).
  - Map coordinate inspection supports keyboard-only coordinate input (`Latitud`, `Longitud`, `Ir` button) in addition to pointer clicks.
- **Non-Color-Only Status Communication:**
  - `DataStatusBadge` and `EvidenceBadge` always pair semantic color tokens with inline SVG icons (`IconCheck`, `IconAlert`, `IconFlask`, `IconBan`, `IconInfo`) and explicit text labels.
- **Accessible Charts:**
  - `ChartFrame` provides `<figure>` / `<figcaption>`, SVG `role="img"` + `<title>`, and an interactive **Tabla accesible** button switching any chart into a semantic `<table>` (`<thead>` / `<tbody>`), tested in `navigationAndAccessibility.test.tsx`.
- **Touch & Mobile Sizing:**
  - Under `@media (max-width: 900px)`, buttons, tabs, inputs, selects, and navigation items enforce `min-height: 44px`.
- **Color Contrast:**
  - Both Light (`#162119` on `#ffffff`, `#1f5c37` with `#ffffff`) and Dark (`#eaf1ec` on `#141e19`, `#4fb075` with `#07140c`) themes are designed to meet WCAG 2.2 AA contrast ratios (≥ 4.5:1 for normal text).

## 2. Verification & Remaining Gaps

- Automated component-level accessibility assertions (landmarks, breadcrumbs, skip-link, role/theme toggles, chart table fallback, non-color badges) pass in Vitest (`src/test/navigationAndAccessibility.test.tsx`).
- Full browser-engine screen-reader (NVDA/JAWS/VoiceOver) and automated Lighthouse/axe-core DOM contrast audit were not executed in this environment (no headless browser runner installed).
