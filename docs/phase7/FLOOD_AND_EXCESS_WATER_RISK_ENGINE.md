# FloodAndExcessWaterRiskEngine — exposición potencial

**Módulo:** `backend/agrosv/monitoring/risks.py`
**Endpoint:** `POST /api/monitoring/flood-risk`
**Versión:** 7.0.0

## Entradas

Lluvia 24 h, lluvia 72 h, pendiente, infiltración del suelo, distancia a
drenaje y zona oficial de inundación (booleano opcional).

## Normalización declarada

| Componente | Escala operativa | Peso |
|---|---|---|
| intensidad 24 h | 20–100 mm | 0,30 |
| antecedente 72 h | 40–200 mm | 0,25 |
| pendiente (escurrimiento) | 0–25° | 0,15 |
| baja infiltración | 50–2 mm/h (invertida) | 0,15 |
| proximidad a drenaje | 5.000–100 m (invertida) | 0,10 |
| zona oficial | 0/1 | 0,05 |

Las escalas son **operativas de AGROSV**, no umbrales oficiales. Si falta un
componente, se renormaliza y se informa.

## Procesos distinguidos

- `surface_water_accumulation` — pendiente baja + 72 h húmedo;
- `waterlogging` — pendiente baja + lluvia o baja infiltración;
- `river_flood_exposure` — drenaje cercano + 72 h húmedo;
- `flash_flood_exposure` — pendiente alta + lluvia intensa;
- `soil_saturation` — 72 h ≥ 100 mm.

Cada bandera es `True`, `False` o `None` (si falta el dato necesario).

## Prohibición

`prediction: false`. No hay modelo hidrológico ni hidráulico, batimetría ni
caudales: el resultado es **exposición potencial**, no una predicción de
inundación ni un daño observado.

## Validación

Pruebas: pendiente 1°, 150 mm en 72 h, infiltración 5 mm/h y drenaje a 500 m
activan acumulación, anegamiento y exposición ribereña; sin variables se lanza
`InsufficientRecordError`.
