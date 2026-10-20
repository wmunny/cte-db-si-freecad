# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versionado [SemVer](https://semver.org/lang/es/).

## [1.0.0] — 2026-10-20

### Añadido
- `SKILL.md` con el procedimiento de verificación y las exigencias de SI 1 a SI 6 y anejos A, B, C, E y F del **DB-SI, texto consolidado de 4 de marzo de 2025** (RD 164/2025).
- Cifras contrastadas con el documento oficial mediante revisión independiente.
- Lectura directa de archivos IFC (`scripts/ifc_extraer.py`, `scripts/ifc_planta.py`) con IfcOpenShell.
- Extracción desde FreeCAD vía MCP (`scripts/freecad_extraer.py`).
- Control de calidad del modelo previo a la verificación (espacios, plantas, uso, puertas, FireRating, estructura, materiales).
- Documentación de instalación para Claude y ChatGPT, conexión MCP con FreeCAD y flujo de trabajo.

### Pendiente (próximas versiones)
- Procedimiento de medición en FreeCAD para SI 2 (ángulo entre fachadas, distancia d, franjas) a partir de las figuras 1.1–1.8 y 2.1.
- Ejemplo completo de informe sobre un modelo de prueba.
