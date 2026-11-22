import React, { useEffect, useState } from "react";
import { ROUTES, routeById, type RouteDef, type RouteId } from "./routes";
import { useApp, type UserRoleProfile } from "../stores/AppContext";
import { GlobalSearchModal } from "../components/navigation/GlobalSearchModal";
import {
  IconAlert,
  IconCalendar,
  IconCoins,
  IconFlask,
  IconHelp,
  IconHome,
  IconLeaf,
  IconMap,
  IconMenu,
  IconMoon,
  IconSatellite,
  IconSearch,
  IconSun,
  IconTerrain,
  IconWifiOff,
} from "../components/icons/Icons";

function RouteIcon({ id }: { id: RouteId }) {
  switch (id) {
    case "home": return <IconHome size={16} />;
    case "map": return <IconMap size={16} />;
    case "territory": return <IconTerrain size={16} />;
    case "crops": return <IconLeaf size={16} />;
    case "calendar": return <IconCalendar size={16} />;
    case "monitoring": return <IconSatellite size={16} />;
    case "risks": return <IconAlert size={16} />;
    case "production":
    case "markets":
    case "profitability":
    case "scenarios":
      return <IconCoins size={16} />;
    case "research":
      return <IconFlask size={16} />;
  }
}

const GROUPS: RouteDef["group"][] = [
  "Explorar",
  "Agronomía y Clima",
  "Vigilancia",
  "Economía",
  "Ciencia",
];

const ROLE_LABELS: Record<UserRoleProfile, string> = {
  farmer: "Productor (Simple)",
  technician: "Técnico agrícola",
  researcher: "Investigador / Estudiante",
  institutional: "Institucional",
};

export function AppShell({
  activeRoute,
  onNavigate,
  children,
}: {
  activeRoute: RouteId;
  onNavigate: (id: RouteId) => void;
  children: React.ReactNode;
}) {
  const {
    resolvedTheme,
    setTheme,
    roleProfile,
    setRoleProfile,
    simpleMode,
    setSimpleMode,
    isOnline,
    selectedLocation,
  } = useApp();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  const current = routeById(activeRoute);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      } else if (e.key === "Escape") {
        setSearchOpen(false);
        setHelpOpen(false);
        setMobileNavOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const navigate = (id: RouteId) => {
    onNavigate(id);
    setMobileNavOpen(false);
  };

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Saltar al contenido principal
      </a>

      {mobileNavOpen && (
        <div
          className="sidebar-scrim"
          aria-hidden="true"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <aside
        className={`app-sidebar ${mobileNavOpen ? "is-open" : ""}`}
        aria-label="Navegación principal"
      >
        <div className="sidebar-brand">
          <a
            href="#/"
            className="brand-mark"
            onClick={(e) => {
              e.preventDefault();
              navigate("home");
            }}
          >
            <span className="brand-crest">SV</span>
            <span>
              <span className="brand-title">AGROSV</span>
              <span className="brand-sub">Inteligencia Agrícola</span>
            </span>
          </a>
        </div>

        <nav className="nav-groups" aria-label="Módulos de AGROSV">
          {GROUPS.map((group) => {
            const items = ROUTES.filter((r) => r.group === group);
            return (
              <div key={group}>
                <div className="nav-group-label">{group}</div>
                <ul className="nav-list">
                  {items.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className="nav-item-btn"
                        aria-current={activeRoute === item.id ? "page" : undefined}
                        onClick={() => navigate(item.id)}
                      >
                        <RouteIcon id={item.id} />
                        <span>{item.label}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </nav>

        <div style={{ padding: "12px 14px", borderTop: "1px solid var(--border-subtle)", fontSize: 12, color: "var(--ink-muted)" }}>
          <div><strong>Ubicación activa:</strong></div>
          <div style={{ color: "var(--ink-primary)", fontWeight: 600 }}>{selectedLocation.label}</div>
          <div className="tabular-nums">
            {selectedLocation.lat.toFixed(3)}°, {selectedLocation.lon.toFixed(3)}°
          </div>
        </div>
      </aside>

      <div className="app-main-col">
        <header className="app-topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-menu-btn"
              aria-label="Abrir menú de navegación"
              aria-expanded={mobileNavOpen}
              onClick={() => setMobileNavOpen((v) => !v)}
            >
              <IconMenu size={18} />
            </button>

            <nav className="breadcrumbs" aria-label="Ruta actual">
              <span>AGROSV</span>
              <span aria-hidden="true">/</span>
              <span>{current.group}</span>
              <span aria-hidden="true">/</span>
              <strong>{current.label}</strong>
            </nav>
          </div>

          <div className="topbar-right">
            {!isOnline && (
              <span className="badge badge--warn" role="status">
                <IconWifiOff size={12} />
                <span>Sin conexión</span>
              </span>
            )}

            <button
              type="button"
              className="btn btn-sm"
              onClick={() => setSearchOpen(true)}
              aria-label="Abrir búsqueda global"
            >
              <IconSearch size={14} />
              <span>Buscar</span>
              <kbd style={{ fontSize: 10.5, opacity: 0.7 }}>Ctrl+K</kbd>
            </button>

            <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12.5 }}>
              <span style={{ color: "var(--ink-muted)" }}>Perfil:</span>
              <select
                className="select"
                style={{ width: "auto", minHeight: 32, padding: "3px 8px", fontSize: 12.5 }}
                aria-label="Perfil de experiencia"
                value={roleProfile}
                onChange={(e) => setRoleProfile(e.target.value as UserRoleProfile)}
              >
                {(Object.keys(ROLE_LABELS) as UserRoleProfile[]).map((k) => (
                  <option key={k} value={k}>{ROLE_LABELS[k]}</option>
                ))}
              </select>
            </label>

            <button
              type="button"
              className="btn btn-sm"
              aria-pressed={!simpleMode}
              onClick={() => setSimpleMode(!simpleMode)}
              title="Alternar entre vista simple y vista técnica avanzada"
            >
              {simpleMode ? "Modo: Simple" : "Modo: Avanzado"}
            </button>

            <button
              type="button"
              className="btn btn-sm"
              onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
              aria-label={resolvedTheme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            >
              {resolvedTheme === "dark" ? <IconSun size={15} /> : <IconMoon size={15} />}
              <span>{resolvedTheme === "dark" ? "Claro" : "Oscuro"}</span>
            </button>

            <button
              type="button"
              className="btn btn-sm"
              onClick={() => setHelpOpen(true)}
              aria-label="Ayuda contextual del módulo"
            >
              <IconHelp size={15} />
            </button>
          </div>
        </header>

        <main
          id="main-content"
          tabIndex={-1}
          className={activeRoute === "map" ? "app-content app-content--map" : "app-content"}
        >
          {children}
        </main>
      </div>

      <GlobalSearchModal
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onNavigate={navigate}
      />

      {helpOpen && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="Ayuda del módulo"
          onClick={(e) => { if (e.target === e.currentTarget) setHelpOpen(false); }}
        >
          <div className="modal-panel">
            <div className="row-wrap" style={{ justifyContent: "space-between", marginBottom: 10 }}>
              <strong style={{ fontSize: 16 }}>Ayuda · {current.label}</strong>
              <button type="button" className="btn btn-sm" onClick={() => setHelpOpen(false)}>Cerrar</button>
            </div>
            <p style={{ margin: "0 0 10px", fontSize: 14, color: "var(--ink-secondary)" }}>{current.description}</p>
            <ul style={{ margin: "0 0 12px 18px", padding: 0, fontSize: 13.5, display: "grid", gap: 6 }}>
              {current.helpTips.map((tip, i) => <li key={i}>{tip}</li>)}
            </ul>
            <div className="callout callout--info" style={{ fontSize: 12.5 }}>
              <strong>Principio de transparencia científica:</strong> AGROSV separa observaciones reales, estadísticas oficiales, reanálisis, predicciones modeladas y simulaciones sintéticas. Cuando un dato no existe en el país o en el repositorio, se informa como <em>No disponible</em>.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
