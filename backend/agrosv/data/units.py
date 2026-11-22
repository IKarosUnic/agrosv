"""AGROSV — registro de unidades y dominios de plausibilidad (Fase 4).

Una cifra sin unidad no es un dato: es un número. Este módulo fija, para cada
variable que AGROSV ingiere, (a) la unidad canónica, (b) las unidades aceptadas
con su conversión exacta y (c) un **rango de error grosero** —no un rango
climático normal— que sirve para rechazar valores imposibles.

Los límites son deliberadamente amplios. Un valor dentro del rango puede ser
científicamente erróneo; un valor fuera del rango es imposible o está en otra
unidad. Que una variable esté «en rango» no la valida (ver
`docs/phase4/SCIENTIFIC_DATA_QUALITY.md`).

Regla dura: una conversión entre unidades incompatibles lanza
`UnitIncompatibleError`. No se adivina la unidad de un archivo a partir de sus
valores: si la unidad no está declarada, el dato queda sin normalizar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class UnitIncompatibleError(ValueError):
    """La unidad declarada no pertenece a la familia de la variable."""


@dataclass(frozen=True)
class VariableSpec:
    """Especificación de una variable: unidad canónica, conversiones y dominio.

    `gross_min`/`gross_max` son cotas de error grosero: fuera de ellas el valor
    es imposible o está escalado. `typical_min`/`typical_max` describen el rango
    esperado en El Salvador cuando se conoce; son informativos y **no** generan
    errores, solo advertencias revisables.
    """

    variable: str
    canonical_unit: str
    conversions: dict[str, tuple[float, float]]  # unidad -> (factor, offset)
    gross_min: float
    gross_max: float
    description: str
    typical_min: float | None = None
    typical_max: float | None = None
    family: str = ""

    def to_canonical(self, values: Any, unit: str) -> Any:
        if unit == self.canonical_unit:
            return values
        if unit not in self.conversions:
            raise UnitIncompatibleError(
                f"{self.variable}: unidad '{unit}' no convertible a "
                f"'{self.canonical_unit}'; aceptadas: "
                f"{sorted(self.conversions)}"
            )
        factor, offset = self.conversions[unit]
        return values * factor + offset

    def as_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "canonical_unit": self.canonical_unit,
            "accepted_units": sorted(self.conversions),
            "gross_domain": [self.gross_min, self.gross_max],
            "typical_range": [self.typical_min, self.typical_max],
            "description": self.description,
            "family": self.family,
        }


def _linear(unit: str, factor: float) -> tuple[str, tuple[float, float]]:
    return unit, (factor, 0.0)


# --- Variables ---------------------------------------------------------------
_SPECS: tuple[VariableSpec, ...] = (
    VariableSpec(
        "precipitation", "mm", dict([
            _linear("mm", 1.0), _linear("cm", 10.0), _linear("m", 1000.0),
            _linear("in", 25.4),
        ]), 0.0, 5000.0,
        "precipitación acumulada en el período declarado",
        typical_min=0.0, typical_max=400.0, family="depth",
    ),
    VariableSpec(
        "temperature", "degC", {
            "degC": (1.0, 0.0), "K": (1.0, -273.15),
            "degF": (5.0 / 9.0, -32.0 * 5.0 / 9.0),
        }, -50.0, 60.0,
        "temperatura del aire a 2 m",
        typical_min=5.0, typical_max=42.0, family="temperature",
    ),
    VariableSpec(
        "relative_humidity", "%", dict([_linear("%", 1.0), _linear("frac", 100.0)]),
        0.0, 100.0, "humedad relativa media", 10.0, 100.0, family="fraction",
    ),
    VariableSpec(
        "et0", "mm", dict([_linear("mm", 1.0), _linear("in", 25.4)]),
        0.0, 100.0, "evapotranspiración de referencia FAO-56 para el período",
        0.0, 20.0, family="depth",
    ),
    VariableSpec(
        "radiation", "MJ m-2 d-1", dict([
            _linear("MJ m-2 d-1", 1.0), _linear("W m-2", 0.0864),
        ]), 0.0, 60.0,
        "radiación solar incidente (factor W m-2 -> MJ m-2 d-1 = 0,0864)",
        0.0, 32.0, family="energy_flux",
    ),
    VariableSpec(
        "wind_speed", "m s-1", dict([_linear("m s-1", 1.0), _linear("km h-1", 1 / 3.6)]),
        0.0, 75.0, "velocidad del viento a 2 o 10 m (declarar altura)",
        0.0, 25.0, family="speed",
    ),
    VariableSpec(
        "elevation", "m", dict([_linear("m", 1.0)]),
        -100.0, 3000.0,
        "elevación sobre el nivel medio del mar (El Salvador: 0–2730 m)",
        0.0, 2730.0, family="length",
    ),
    VariableSpec(
        # La pendiente en % NO es convertible con un factor lineal: % = tan(deg)·100.
        # Se rechaza en lugar de convertirla mal; use `slope_pct_to_deg`.
        "slope", "deg", dict([_linear("deg", 1.0)]),
        0.0, 90.0, "pendiente del terreno en grados (la pendiente en % se "
        "convierte con arctan, no con un factor)",
        0.0, 75.0, family="angle",
    ),
    VariableSpec(
        "aspect", "deg", dict([_linear("deg", 1.0)]),
        0.0, 360.0, "orientación de la pendiente (0–360, 0=norte)",
        0.0, 360.0, family="angle",
    ),
    VariableSpec(
        "ph", "", dict([_linear("", 1.0)]),
        0.0, 14.0, "pH medido o predicho (suspensión 1:2,5 si se declara)",
        4.0, 9.0, family="chemistry",
    ),
    VariableSpec(
        "clay", "%", dict([_linear("%", 1.0), _linear("g kg-1", 0.1)]),
        0.0, 100.0, "contenido de arcilla (<2 µm)",
        0.0, 100.0, family="fraction",
    ),
    VariableSpec(
        "sand", "%", dict([_linear("%", 1.0), _linear("g kg-1", 0.1)]),
        0.0, 100.0, "contenido de arena (2–2000 µm)",
        0.0, 100.0, family="fraction",
    ),
    VariableSpec(
        "silt", "%", dict([_linear("%", 1.0), _linear("g kg-1", 0.1)]),
        0.0, 100.0, "contenido de limo (2–50 µm)",
        0.0, 100.0, family="fraction",
    ),
    VariableSpec(
        "soil_organic_carbon", "g kg-1", dict([
            _linear("g kg-1", 1.0), _linear("%", 10.0), _linear("dg kg-1", 0.1),
        ]), 0.0, 600.0, "carbono orgánico del suelo",
        0.0, 200.0, family="concentration",
    ),
    VariableSpec(
        "soil_nitrogen", "g kg-1", dict([
            _linear("g kg-1", 1.0), _linear("cg kg-1", 0.01), _linear("%", 10.0),
        ]), 0.0, 100.0, "nitrógeno total del suelo",
        0.0, 20.0, family="concentration",
    ),
    VariableSpec(
        "soil_moisture", "m3 m-3", dict([_linear("m3 m-3", 1.0), _linear("%", 0.01)]),
        0.0, 1.0, "contenido volumétrico de agua en el suelo",
        0.0, 0.6, family="fraction",
    ),
    VariableSpec(
        "ndvi", "", dict([_linear("", 1.0)]),
        -1.0, 1.0, "índice de vegetación de diferencia normalizada", -0.3, 1.0,
        family="index",
    ),
    VariableSpec(
        "ndwi", "", dict([_linear("", 1.0)]),
        -1.0, 1.0, "índice de agua de diferencia normalizada", -1.0, 1.0,
        family="index",
    ),
    VariableSpec(
        "land_cover_class", "class", dict([_linear("class", 1.0)]),
        0.0, 999.0, "código de clase (el dominio real lo fija la leyenda)",
        0.0, 999.0, family="categorical",
    ),
    VariableSpec(
        # El quintal no tiene una masa única (46 kg café oro, 100 lb, etc.):
        # convertir sin declararla sería inventar el factor.
        "yield", "t ha-1", dict([_linear("t ha-1", 1.0),
                                 _linear("kg ha-1", 0.001)]),
        0.0, 200.0, "rendimiento agrícola en t/ha; el quintal/manzana exige "
        "declarar la masa del quintal y se convierte fuera del registro",
        0.0, 30.0, family="areal_mass",
    ),
    VariableSpec(
        "production", "t", dict([_linear("t", 1.0), _linear("kg", 0.001)]),
        0.0, 1e8, "producción total en toneladas métricas (el quintal exige "
        "declarar su masa)", 0.0, None,
        family="mass",
    ),
    VariableSpec(
        "area", "ha", dict([_linear("ha", 1.0), _linear("km2", 100.0),
                            _linear("mz", 0.6988)]),
        0.0, 5e6, "superficie (1 manzana = 0,6988 ha, valor adoptado por MAG)",
        0.0, None, family="area",
    ),
    VariableSpec(
        "price", "USD", dict([_linear("USD", 1.0)]),
        0.0, 1e6, "precio monetario (declarar moneda, plaza y presentación)",
        0.0, None, family="money",
    ),
    VariableSpec(
        "nutrient", "mg kg-1", dict([_linear("mg kg-1", 1.0),
                                        _linear("ppm", 1.0)]),
        0.0, 50_000.0, "nutriente extractable del suelo; el método de extracción "
        "(Olsen, KCl, DTPA…) debe declararse porque cambia el valor",
        0.0, None, family="concentration",
    ),
    VariableSpec(
        "soil_depth", "cm", dict([_linear("cm", 1.0), _linear("m", 100.0)]),
        0.0, 300.0, "profundidad de suelo (efectiva o de muestreo, declarar cuál)",
        0.0, 200.0, family="length",
    ),
    VariableSpec(
        "discharge", "m3 s-1", dict([_linear("m3 s-1", 1.0),
                                        _linear("L s-1", 0.001)]),
        0.0, 20_000.0, "caudal instantáneo o medio del período declarado",
        0.0, None, family="volumetric_flow",
    ),
    VariableSpec(
        "water_level", "m", dict([_linear("m", 1.0)]),
        -50.0, 500.0, "nivel de agua (río, pozo, lago); declarar datum o "
        "nivel de referencia", 0.0, 50.0, family="length",
    ),
)

REGISTRY: dict[str, VariableSpec] = {s.variable: s for s in _SPECS}

# Variables sin unidad física: nunca se exige unidad para ellas.
UNITLESS_VARIABLES = frozenset({"time", "date", "period", "class", "id"})


def spec(variable: str) -> VariableSpec | None:
    return REGISTRY.get(variable.strip().lower())


def convert(values: Any, variable: str, from_unit: str, to_unit: str | None = None) -> Any:
    """Convierte a la unidad canónica (o a `to_unit` si es la canónica)."""
    s = spec(variable)
    if s is None:
        raise UnitIncompatibleError(
            f"variable '{variable}' no registrada: declare su unidad y dominio "
            "en agrosv.data.units antes de normalizarla"
        )
    target = to_unit or s.canonical_unit
    if target != s.canonical_unit:
        raise UnitIncompatibleError(
            f"{variable}: la unidad canónica es '{s.canonical_unit}'; "
            f"no se convierte a '{target}'"
        )
    return s.to_canonical(values, from_unit)


def check_unit(variable: str, declared_unit: str | None) -> dict[str, Any]:
    """Comprueba compatibilidad de unidad sin convertir. Devuelve un hallazgo."""
    s = spec(variable)
    if s is None:
        return {"variable": variable, "ok": False, "severity": "warning",
                "detail": "variable no registrada: no se puede verificar la unidad"}
    if variable in UNITLESS_VARIABLES:
        return {"variable": variable, "ok": True, "severity": "info",
                "detail": "variable sin unidad física"}
    if not declared_unit:
        return {"variable": variable, "ok": False, "severity": "error",
                "detail": f"unidad no declarada; canónica '{s.canonical_unit}'"}
    ok = declared_unit == s.canonical_unit or declared_unit in s.conversions
    return {
        "variable": variable,
        "ok": ok,
        "severity": "info" if ok else "error",
        "declared": declared_unit,
        "canonical": s.canonical_unit,
        "detail": ("unidad aceptada" if ok else
                   f"unidad incompatible; aceptadas {sorted(s.conversions)}"),
    }


def gross_domain_check(variable: str, values: Any) -> dict[str, Any]:
    """Valores imposibles fuera del dominio de error grosero (no climático).

    Devuelve conteos, no una decisión: la política de severidad la aplica
    `agrosv.data.quality`, que distingue error de advertencia.
    """
    s = spec(variable)
    if s is None:
        return {"variable": variable, "checked": False,
                "detail": "variable no registrada"}
    arr = [v for v in values if v is not None and v == v]
    below = sum(1 for v in arr if v < s.gross_min)
    above = sum(1 for v in arr if v > s.gross_max)
    return {
        "variable": variable,
        "checked": True,
        "n": len(arr),
        "below": below,
        "above": above,
        "outside": below + above,
        "domain": [s.gross_min, s.gross_max],
        "unit": s.canonical_unit,
    }


def registry() -> dict[str, Any]:
    return {"variables": [s.as_dict() for s in _SPECS],
            "note": ("gross_domain es un rango de error grosero, no un rango "
                     "climático normal ni un criterio de calidad científica")}
