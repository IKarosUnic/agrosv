import React from "react";
import { EvidenceBadge } from "../data-status/DataStatus";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {actions && <div className="row-wrap">{actions}</div>}
    </header>
  );
}

export function MetricCard({
  label,
  value,
  unit,
  detail,
  evidenceClass,
  synthetic,
  date,
}: {
  label: string;
  value: string;
  unit?: string;
  detail?: string;
  evidenceClass?: string;
  synthetic?: boolean;
  date?: string | null;
}) {
  return (
    <div className="card">
      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--ink-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {label}
      </div>
      <div className="tabular-nums" style={{ fontSize: 22, fontWeight: 700, marginTop: 6, color: "var(--ink-primary)" }}>
        {value}
        {unit && <span style={{ fontSize: 13, fontWeight: 500, color: "var(--ink-muted)", marginLeft: 4 }}>{unit}</span>}
      </div>
      {detail && <div style={{ fontSize: 12.5, color: "var(--ink-secondary)", marginTop: 4 }}>{detail}</div>}
      {(evidenceClass || synthetic || date) && (
        <div className="row-wrap" style={{ marginTop: 10, justifyContent: "space-between" }}>
          {(evidenceClass || synthetic) && <EvidenceBadge evidenceClass={evidenceClass} synthetic={synthetic} />}
          {date && <span style={{ fontSize: 11.5, color: "var(--ink-muted)" }}>{date.slice(0, 10)}</span>}
        </div>
      )}
    </div>
  );
}
