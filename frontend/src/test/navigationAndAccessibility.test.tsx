import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AppProvider } from "../stores/AppContext";
import { AppShell } from "../app/AppShell";
import { ChartFrame, SvgBarChart } from "../components/charts/Charts";
import { DataStatusBadge, EvidenceBadge } from "../components/data-status/DataStatus";

describe("Navigation, theme switching, accessibility, and data presentation", () => {
  it("renders accessible AppShell landmarks, breadcrumbs, theme switcher, and profile modes", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ features: [], crops: [], result: { markets: [] }, pests: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ));

    const onNavigate = vi.fn();
    render(
      <AppProvider>
        <AppShell activeRoute="crops" onNavigate={onNavigate}>
          <div>Contenido cultivos</div>
        </AppShell>
      </AppProvider>,
    );

    expect(screen.getByText("Saltar al contenido principal")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Ruta actual" })).toHaveTextContent("Cultivos");

    // Toggle dark theme
    const themeBtn = screen.getByRole("button", { name: /Cambiar a modo oscuro/i });
    fireEvent.click(themeBtn);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

    // Switch role profile
    const roleSelect = screen.getByLabelText("Perfil de experiencia");
    fireEvent.change(roleSelect, { target: { value: "researcher" } });
    expect((roleSelect as HTMLSelectElement).value).toBe("researcher");

    // Navigate via sidebar
    fireEvent.click(screen.getByRole("button", { name: "Rentabilidad" }));
    expect(onNavigate).toHaveBeenCalledWith("profitability");
  });

  it("provides an accessible tabular alternative for charts", () => {
    render(
      <ChartFrame
        title="Precipitación mensual"
        unit="mm"
        source="Open-Meteo"
        rows={[{ Mes: "Ene", Valor: 12 }, { Mes: "Feb", Valor: null }]}
      >
        <SvgBarChart data={[{ label: "Ene", value: 12 }, { label: "Feb", value: null }]} unit="mm" />
      </ChartFrame>,
    );

    expect(screen.getByRole("img")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tabla accesible" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Sin dato")).toBeInTheDocument();
  });

  it("renders non-color-only badges for synthetic and unavailable states", () => {
    render(
      <div>
        <EvidenceBadge synthetic />
        <DataStatusBadge tone="unavailable" label="Sin datos" />
      </div>,
    );
    expect(screen.getByText(/Simulación sintética/i)).toBeInTheDocument();
    expect(screen.getByText("Sin datos")).toBeInTheDocument();
  });
});
