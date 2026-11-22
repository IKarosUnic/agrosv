import React from "react";
import { EVIDENCE_LABELS } from "../../utils/format";
import { IconAlert, IconBan, IconCheck, IconFlask, IconInfo, IconWifiOff } from "../icons/Icons";

export type BadgeTone = "ok" | "warn" | "crit" | "info" | "unavailable" | "synthetic";

function ToneIcon({ tone }: { tone: BadgeTone }) {
  if (tone === "ok") return <IconCheck size={12} />;
  if (tone === "warn" || tone === "crit") return <IconAlert size={12} />;
  if (tone === "synthetic") return <IconFlask size={12} />;
  if (tone === "unavailable") return <IconBan size={12} />;
  return <IconInfo size={12} />;
}

export function DataStatusBadge({
  tone,
  label,
}: {
  tone: BadgeTone;
  label: string;
}) {
  return (
    <span className={`badge badge--${tone}`}>
      <ToneIcon tone={tone} />
      <span>{label}</span>
    </span>
  );
}

export function EvidenceBadge({
  evidenceClass,
  synthetic,
}: {
  evidenceClass?: string | null;
  synthetic?: boolean;
}) {
  if (synthetic) {
    return (
      <DataStatusBadge
        tone="synthetic"
        label="Simulación sintética — no es observación real"
      />
    );
  }
  const key = (evidenceClass ?? "unavailable").toLowerCase();
  const meta = EVIDENCE_LABELS[key] ?? { label: key, tone: "info" as const };
  return <DataStatusBadge tone={meta.tone} label={meta.label} />;
}

export function SourceAttribution({
  sources,
  date,
  resolution,
}: {
  sources?: Array<Record<string, unknown> | string>;
  date?: string | null;
  resolution?: string | null;
}) {
  if (!sources?.length && !date && !resolution) return null;
  const formattedSources = (sources ?? []).map((s) =>
    typeof s === "string"
      ? s
      : String(s.name ?? s.dataset_id ?? s.institution ?? "Fuente registrada"),
  );
  return (
    <div className="hint small" style={{ fontSize: 12, color: "var(--ink-muted)", marginTop: 8 }}>
      {formattedSources.length > 0 && (
        <span>
          <strong>Fuente:</strong> {formattedSources.join(" · ")}
        </span>
      )}
      {date && (
        <span>
          {formattedSources.length > 0 ? " · " : ""}
          <strong>Fecha:</strong> {date.slice(0, 10)}
        </span>
      )}
      {resolution && (
        <span>
          {(formattedSources.length > 0 || date) ? " · " : ""}
          <strong>Resolución:</strong> {resolution}
        </span>
      )}
    </div>
  );
}

export function UncertaintyPanel({
  assumptions,
  limitations,
  uncertainty,
  collapsedByDefault = false,
}: {
  assumptions?: string[];
  limitations?: string[];
  uncertainty?: string | Record<string, unknown> | null;
  collapsedByDefault?: boolean;
}) {
  const hasContent = Boolean(assumptions?.length || limitations?.length || uncertainty);
  if (!hasContent) return null;
  const uncText =
    typeof uncertainty === "string"
      ? uncertainty
      : uncertainty
        ? String(uncertainty.note ?? uncertainty.method ?? JSON.stringify(uncertainty))
        : null;

  return (
    <details open={!collapsedByDefault} style={{ marginTop: 10 }}>
      <summary style={{ cursor: "pointer", fontSize: 12.5, fontWeight: 600, color: "var(--ink-secondary)" }}>
        Incertidumbre, supuestos y limitaciones metodológicas
      </summary>
      <div className="stack-sm" style={{ marginTop: 8, fontSize: 12.5, color: "var(--ink-secondary)" }}>
        {uncText && (
          <div>
            <strong>Incertidumbre:</strong> {uncText}
          </div>
        )}
        {assumptions && assumptions.length > 0 && (
          <div>
            <strong>Supuestos:</strong>
            <ul style={{ margin: "4px 0 0 18px", padding: 0 }}>
              {assumptions.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </div>
        )}
        {limitations && limitations.length > 0 && (
          <div>
            <strong>Limitaciones:</strong>
            <ul style={{ margin: "4px 0 0 18px", padding: 0 }}>
              {limitations.map((l, i) => <li key={i}>{l}</li>)}
            </ul>
          </div>
        )}
      </div>
    </details>
  );
}

export function LoadingState({ message = "Consultando motores científicos…" }: { message?: string }) {
  return (
    <div className="card" role="status" aria-live="polite" style={{ padding: 20 }}>
      <span style={{ color: "var(--ink-muted)", fontSize: 13.5 }}>{message}</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="card" style={{ padding: 20 }}>
      <DataStatusBadge tone="unavailable" label="Sin datos disponibles" />
      <h3 style={{ margin: "10px 0 4px", fontSize: 15 }}>{title}</h3>
      <p style={{ margin: 0, fontSize: 13.5, color: "var(--ink-muted)" }}>{description}</p>
      {action && <div style={{ marginTop: 12 }}>{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Servicio o capa no disponible",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="callout callout--warn" role="alert">
      <IconAlert size={18} />
      <div style={{ flex: 1 }}>
        <strong>{title}</strong>
        <div style={{ marginTop: 3, color: "var(--ink-secondary)" }}>{message}</div>
        {onRetry && (
          <button type="button" className="btn btn-sm" onClick={onRetry} style={{ marginTop: 8 }}>
            Reintentar
          </button>
        )}
      </div>
    </div>
  );
}

export function CacheNotice({ cachedAt }: { cachedAt: string | null }) {
  if (!cachedAt) return null;
  return (
    <div className="callout callout--info" role="status" style={{ marginBottom: 12 }}>
      <IconWifiOff size={16} />
      <div>
        <strong>Copia en caché local (sin conexión en vivo).</strong> Última sincronización:{" "}
        <span className="tabular-nums">{cachedAt.replace("T", " ").slice(0, 19)} UTC</span>.
        Los datos en caché pueden no reflejar actualizaciones recientes.
      </div>
    </div>
  );
}
