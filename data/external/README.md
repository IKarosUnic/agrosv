# Datos externos aportados por el usuario

Este directorio es la zona de entrega para archivos que **no** se descargan
automáticamente: series SNET/MARN, muestras del Laboratorio de Suelos CENTA,
cuencas oficiales, aforos y puntos GNSS.

Reglas:

1. Los archivos aquí **no** se versionan (ver `.gitignore`).
2. No se suben datos restringidos sin autorización escrita.
3. Cada archivo debe conservar su fuente, fecha, licencia y unidad.
4. La validación no corrige ni imputa valores: rechaza o advierte.
5. Un archivo válido no se convierte en dato oficial hasta documentar su
   procedencia y validación.

Validación:

```bash
.venv/bin/python scripts/11_validate_external_data.py \
  --kind station_series --path data/external/estaciones.csv
```

Tipos admitidos: `station_series`, `centa_samples`, `basins`, `gauging`,
`crosswalk`, `gnss`.

Esquemas y solicitudes: `docs/phase7/DATA_ACCESS_AND_ONBOARDING.md` y
`docs/phase7/DATA_REQUEST_TEMPLATES.md`.
