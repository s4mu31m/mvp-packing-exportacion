# MVP Packing Exportacion

Repositorio tecnico del sistema de trazabilidad y operacion de packing para exportacion.

## Fuente documental canonica

La **wiki del proyecto** es la unica fuente documental canonica para alcance, flujo, modelo de datos y arquitectura:

- <https://github.com/s4mu31m/mvp-packing-exportacion/wiki>

En este repositorio solo se mantiene documentacion operativa local (setup, integracion y pruebas).

## Documentacion local vigente

- [`DATAVERSE_GUIDE.md`](DATAVERSE_GUIDE.md)
- [`python-app/README.md`](python-app/README.md)
- [`python-app/SETUP.md`](python-app/SETUP.md)
- [`python-app/TESTING_DATAVERSE.md`](python-app/TESTING_DATAVERSE.md)
- [`python-app/tests/e2e/readme.md`](python-app/tests/e2e/readme.md)

## Capacidades actuales

- Flujo operativo web: `recepcion -> desverdizado -> ingreso packing -> proceso -> control -> paletizado -> camaras`.
- Backend dual de persistencia (`sqlite` y `dataverse`) con la misma capa de casos de uso.
- API operativa en `/api/operaciones/` para bins, lotes, pallets, eventos y trazabilidad.
- Endpoints de diagnostico Dataverse en `/api/dataverse/`.
- Control de acceso por rol en portal operativo y modulo de consulta/exportacion.

## Estructura principal

```text
mvp-packing-exportacion/
|-- .github/
|-- scripts/dataverse/
|-- python-app/
|   |-- README.md
|   |-- SETUP.md
|   |-- TESTING_DATAVERSE.md
|   `-- src/
|-- DATAVERSE_GUIDE.md
`-- README.md
```

## Checklist editorial de mantenimiento

- No duplicar en el repo contenido canónico que ya viva en la wiki.
- No registrar bitacoras de ejecucion, reportes operativos ni historiales por iteracion en documentacion oficial.
- Actualizar la documentacion por **capacidades vigentes del sistema**, no por hitos temporales.
- Ante conflicto entre repo y wiki, prevalece la wiki.

