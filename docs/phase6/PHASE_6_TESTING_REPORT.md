# Informe de pruebas — Fase 6

**Fecha: 2026-11-22 · Estado: 469 pruebas pasan, 0 fallos, 0 omitidas**

## Comando

```bash
cd /workspace/chats/b87a4c6cc910e4fa27d25f33
.venv/bin/python -m pytest tests -q
```

## Resultado

| Suite | Pruebas | Resultado |
|---|---|---|
| Fase 1–5 (existente) | 373 | pasan |
| `test_phase6_agriculture.py` | 37 | pasan |
| `test_phase6_social.py` | 37 | pasan |
| `test_phase6_integration.py` | 22 | pasan |
| **Total** | **469** | **0 fallos, 0 omitidas** |

Tiempo observado: ~36 s para la suite completa; ~12 s para las tres suites de
Fase 6.

## Cobertura por área

### Agrícola

* 22 fichas, unicidad, estados, GAP = `null`, 5 cultivos simulables.
* Búsqueda con acentos; comparación REF/NAC.
* GDD: método de la media, piso en 0, acumulación, etapas, series incompletas,
  fracciones inválidas, ausencia de Tbase.
* Aptitud: ventana circular, NoData ⇒ `not_evaluated`, factores presentes,
  sistema urbano no evaluado, riego condicionado a supuesto, cultivo inválido.
* Agua: lluvia efectiva, Kc, rechazo sin AWC, estrés, programación de riego.
* Nutrientes: remoción, fuente obligatoria, GAP.
* Simulación: único adaptador ejecutable, rechazo de externos, rendimiento
  nulo sin Ym/Ky, estados de calibración.
* Calendario: ventanas, riesgos, clasificación, GAP.

### Social

* Reproducibilidad por semilla; diferencia entre semillas.
* Rechazo de arquetipos y tamaños inválidos; límite de 100.000.
* Separación de capas; rechazo de campo agrícola en `SOURCE_PROFILE`; rechazo
  de observado sintético.
* Muestra Nemotron: 3 filas, 0 agrícolas; no reasignación de rol.
* Hogar: consistencia, límites, minimización.
* Comportamiento: aversión al riesgo, restricciones duras, aprendizaje acotado.
* Economía: validación de fuente/fecha/moneda/unidad, precio faltante, margen,
  umbrales, moneda incompatible.
* Adopción: barrera de agua, índice [0,1], tecnología inválida.
* Resiliencia: choque inválido, componentes, monotonicidad capacidad-impacto.
* Multiagente: reproducibilidad, historial, rechazo de pasos/choque inválidos.

### Integración y API

* Perfil sin AWC declara `not_evaluated`; con AWC ejecuta balance.
* Decisión sin cultivo evaluable; determinismo; restricción de capital.
* Escenarios: inválido, tamaño máximo, métricas, capas, economía con hojas.
* Análisis: comparación, hallazgos marcados como simulación, restricciones.
* API: catálogo, 404, 400 de coordenadas, simulación sin pronóstico,
  declaración sintética, escenario y análisis, endpoints de Fase 5 intactos.

## Benchmarks

`docs/phase6/benchmark_phase6.json`:

| Operación | Mediana | Memoria pico |
|---|---|---|
| población 100 | 0,051 s | 1,08 MB |
| población 1.000 | 0,508 s | 2,32 MB |
| población 5.000 | 2,575 s | 11,49 MB |
| multiagente 1.000, 10 pasos | 0,113 s | 1,07 MB |
| aptitud café | 0,133 s | 12,21 MB |
| fenología maíz | 0,028 s | 2,53 MB |
| balance maíz | 0,026 s | 2,10 MB |
| escenario 50 agentes | 3,207 s | 2,54 MB |

Medido con `tracemalloc` en un proceso local; no es RSS ni un SLA.

## Lo que las pruebas no establecen

* No validan parámetros agronómicos.
* No validan arquetipos contra el CAP 2025.
* No validan decisiones ni adopción contra personas reales.
* No prueban el determinismo entre versiones de NumPy.
* No cubren concurrencia ni múltiples workers.

**Una prueba que pasa no convierte una simulación en ciencia validada.**
