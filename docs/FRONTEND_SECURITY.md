# AGROSV — Security & Privacy (`docs/FRONTEND_SECURITY.md`)

## 1. Implemented Frontend Security Practices

- **Zero Secret Keys:** No API keys, tokens, or credentials exist in `frontend/`. All backend communication uses same-origin `/api/*` paths (proxied in Vite dev, served directly by FastAPI in production).
- **XSS Prevention:** Zero `dangerouslySetInnerHTML`, `eval`, or raw HTML injection anywhere in `frontend/src/`. All API strings render through React JSX text escaping.
- **URL & Query Encoding:** All path/query parameters (`crop_id`, `department`, `district`, `alert_id`, `q`) are encoded with `encodeURIComponent` or `URLSearchParams`.
- **Privacy & Synthetic Separation:**
  - Field observation forms default `publish_coordinates` to omitted/`false`, mirroring `AgriculturalFieldVerificationEngine`'s ~1 km coordinate rounding in public views.
  - Nemotron Profiles (`ScenariosPage`) only display aggregate/occupation/department/age attributes labeled synthetic and never expose real household records.
- **Honest Role Modeling:** Because the FastAPI backend does not implement authentication or RBAC, the frontend profile selector (`Productor`, `Técnico`, `Investigador`, `Institucional`) strictly controls UI complexity and never claims client-side security enforcement.
- **Controlled Error Messages:** `ApiError` extracts structured backend error details cleanly without dumping stack traces in user-facing alerts.
