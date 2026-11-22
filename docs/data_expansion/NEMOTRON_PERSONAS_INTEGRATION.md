# NEMOTRON_PERSONAS_INTEGRATION — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Dataset:** `nvidia/Nemotron-Personas-El-Salvador`.
**Regla superior:** los agentes sintéticos **no sustituyen** encuestas, censos ni
productores reales. No son evidencia estadística de nada.

---

## 1. Hechos verificados del dataset

| Campo | Valor | Fuente |
|---|---|---|
| ID | `nvidia/Nemotron-Personas-El-Salvador` | Hugging Face API (200, 3.731 B) |
| Licencia | **CC BY 4.0** | Metadatos del Hub |
| `gated` | `false` | Metadatos del Hub |
| `sha` (versión inmutable) | `68f6a21c17973d6a34ac6354d50a31c1fbcec14f` | Metadatos del Hub |
| `lastModified` | 2026-06-05 | Metadatos del Hub |
| Filas × columnas | **148.000 × 25** | Datasets Server |
| Parquet | 3 shards; 568.403.131 B (542 MiB) | Hub API |
| Idioma | español salvadoreño (`es`) | Dataset card |
| Anclaje declarado | CPV 2024 (6.029.976 personas) y EHPM 2024 | Dataset card |
| Ocupaciones | CIIU Rev.4, 119 clases; 8 categorías de empleo censales | Dataset card |
| Geografía | 14 departamentos, **44 municipios** (reforma 2023) | Estadísticas del Datasets Server |
| Edad | 18–100 (media 42,8; mediana 40) | Estadísticas |
| Urbano / rural | 73,69 % / 26,31 % | Estadísticas |
| Sexo | femenino 53,81 % / masculino 46,19 % | Estadísticas |

**Muestra descargada y validada** (no se baja el parquet completo):
`data/samples/phase3/nemotron_rows/nemotron_rows_sample.json` (3 filas, 27.580 B,
sha256 `59ea5ead123c…`).

### 1.1 Perfiles con ocupación agrícola primaria (CIIU división 01)

Suma calculada por AGROSV sobre las frecuencias oficiales del Datasets Server:

| Clase CIIU | Registros | % del total |
|---|---:|---:|
| Cultivo de cereales, legumbres y semillas oleaginosas | 9.324 | 6,30 % |
| Cultivo de café, cacao y té | 1.950 | 1,32 % |
| Otras actividades agropecuarias | 1.806 | 1,22 % |
| Explotación mixta | 1.532 | 1,03 % |
| Hortalizas, raíces y tubérculos | 966 | 0,65 % |
| Ganado bovino y búfalos | 859 | 0,58 % |
| Aves de corral | 851 | 0,57 % |
| Caña de azúcar | 669 | 0,45 % |
| **Total división 01** | **17.957** | **12,13 %** |

**Diferencia que debe declararse siempre:** 17.957 agentes ≈ población ocupada en
agricultura; 401.101 es el número de productores de maíz del CAP 2025. Son
universos distintos (personas ocupadas vs. unidades de producción, que incluyen
producción de patio y familiares no remunerados). No es un error de datos.

---

## 2. Limitaciones declaradas (por el editor, no inferidas)

- Subrepresentación de identidades indígenas (Náhuat-Pipil, Lenca, Kakawira) y
  afrodescendientes.
- Roles de género heredados del modelo narrativo.
- Español salvadoreño aproximado por generación, no extraído de corpus autorizado.
- Religión no modelada.
- **Independencia asumida** entre ocupación y nivel educativo dado departamento,
  edad y sexo.
- Sin nombres individuales (mitigación de reidentificación).
- Solo adultos.
- **Sin campos de:** tamaño de finca, tenencia, ingreso, acceso a agua, crédito,
  superficie sembrada, activos, maquinaria.

**Consecuencia:** el dataset no permite, por sí solo, modelar decisiones
económicas de un productor. Hay que **añadir una capa de dotaciones derivada de
fuentes reales** (CAP 2025, CPV 2024) y etiquetarla como asignación, no como
observación.

---

## 3. Arquetipos de productor para AGROSV

Cada arquetipo se define por **reglas explícitas** sobre variables existentes; no
se inventan distribuciones.

| Arquetipo | Regla de selección (sobre Nemotron) | Dotaciones a añadir (fuente) | Incertidumbre |
|---|---|---|---|
| **Subsistencia** | ocupación CIIU 0111/0113 + área rural + edad 30–70 | superficie < 2 mz, autoconsumo > 50 % (CAP 2025 nacional) | Alta: el censo no desagrega por persona |
| **Pequeño comercial** | CIIU 0111/0113/0127 + urbano-periurbano | superficie 2–10 mz, venta > 50 % (CAP) | Alta |
| **Tecnificado** | CIIU 0111/0121 + municipio de alta concentración de maíz/caña | riego, mecanización, híbrido (CAP) | Media-alta |
| **Periurbano** | municipio del AMSS + CIIU 01 | acceso a mercado mayorista (MAG) | Media |
| **Urbano** | área urbana + CIIU 01 | producción en patio (CAP sección 3) | Alta |
| **Cooperativa** | no identificable en Nemotron | membresía (MAG/CENTA; no hay registro abierto) | **No modelable** sin fuente |
| **Sin acceso al agua** | municipio con menor cobertura (CPV 2024) | acceso a agua por hogar (CPV) | Media |

**Los arquetipos no son categorías oficiales.** Se nombran como tipos analíticos
AGROSV y no se presentan como clasificación del MAG.

---

## 4. Metodología multiagente propuesta

### 4.1 Arquitectura

```
Nemotron (perfil base)  ──►  capa de dotaciones (CAP/CPV)  ──►  agente
                                                                    │
      clima (CHIRPS/POWER) + suelo + precios (MAG) ────────────────►│
                                                                    ▼
                                                        motor de decisión
                                                                    │
                                                                    ▼
                                                     resultado + bandas de sensibilidad
```

### 4.2 Reglas de simulación

1. **Semilla y versión fijas:** mismo `sha` del dataset, misma configuración →
   mismos resultados.
2. **Decisiones acotadas:** el agente elige entre un conjunto finito de prácticas
   documentadas (siembra temprana/tardía, híbrido/criollo, riego/no riego), no
   inventa tecnologías.
3. **Restricciones reales:** presupuesto y acceso a agua se imponen como
   restricciones duras, no como preferencias.
4. **Sin optimización perfecta:** se usa racionalidad limitada con umbrales
   declarados.
5. **Salida como distribución:** 1.000–10.000 corridas por escenario, se reporta
   P10/P50/P90, nunca un único número.
6. **Validación agregada:** la media simulada se compara con el CAP 2025
   departamental; si la desviación > 30 %, el escenario se marca como no válido.

### 4.3 Qué se puede y qué no se puede preguntar

| Permitido | Prohibido |
|---|---|
| «¿Cómo cambia la distribución de siembra si la lluvia llega 3 semanas tarde?» | «¿Este productor recibirá el paquete agrícola?» |
| «¿Qué proporción de perfiles podría adoptar riego suplementario?» | Estimar ingreso o crédito de una persona real |
| Explorar heterogeneidad de respuestas | Publicar un «productor típico» como si fuera observado |
| Generar hipótesis para encuestas | Sustituir una encuesta o censo |

---

## 5. Ética y gobernanza

- Los perfiles son **sintéticos**: la UI debe mostrarlo en cada resultado.
- No se enlazan con el CPV a nivel de persona.
- No se usan para elegibilidad, crédito, seguro ni focalización de programas.
- No se generan atributos sensibles (religión, etnia, salud) que el dataset evita.
- Toda simulación guarda: `sha` del dataset, versión del código, semilla, supuestos.

---

## 6. Estado de implementación

| Componente | Estado |
|---|---|
| Verificación del dataset y licencia | **Hecho** (2026-11-22) |
| Muestra de filas y estadísticas | **Hecho** |
| Definición de arquetipos | **Diseñada** (este documento) |
| Capa de dotaciones | **Pendiente** — requiere tablas del CAP/CPV |
| Motor multiagente | **No implementado** |
| Validación contra censo | **Pendiente** |

No se declara operativo ningún simulador de productores: sería presentar un
diseño como resultado.
