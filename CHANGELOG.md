# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versionado [SemVer](https://semver.org/lang/es/).

## [1.1.0] — 2026-10-20

Mejoras surgidas de las pruebas reales con ChatGPT Desktop + MCP de FreeCAD (dibujo 2D → BIM → informe).

### Añadido
- Nuevos estados de resultado: **`ERROR DE MODELO`** (incoherencias del modelo, como recintos sin acceso, que no son incumplimientos del proyecto) e **`INFO`** (cálculos como la ocupación, que no se cuentan como CUMPLE).
- **Preguntas priorizadas**: primero las imprescindibles, el resto sólo si el edificio lo requiere, en un único mensaje.
- Criterio explícito de **cuándo aplica cada exigencia de SI 2** (NO APLICA frente a NO VERIFICABLE).
- Estimación de recorridos por malla y comprobación de conectividad de recintos en las reglas del informe.
- Regla de conclusión: "cumplimiento acreditado" sólo sin NO CUMPLE, NO VERIFICABLE ni ERROR DE MODELO relevantes.
- `docs/tutorial-del-croquis-al-informe.md`: ejercicio pedagógico completo con prompts y resultados.

### Corregido
- `freecad_extraer.py` e `ifc_planta.py`: la geometría se leía encadenando `create_shape(...).geometry.verts`; con algunas versiones de IfcOpenShell (la incluida en FreeCAD) el objeto se liberaba antes y las cajas envolventes salían vacías (sin espesores de muro ni posiciones). Detectado en la prueba con ChatGPT Desktop + MCP FreeCAD.
- `freecad_extraer.py` (BIM clásico): ahora lee el uso declarado en el edificio (IfcProperties, propiedad propia o descripción).
- `freecad_extraer.py`: los elementos PCI sólo se cuentan si son objetos BIM; antes contaba también símbolos y textos 2D con "extintor" en el nombre (p. ej. del dibujo original oculto).

## [1.0.1] — 2026-10-20

### Corregido
- `freecad_extraer.py` no reconocía los IFC abiertos en **modo nativo** de FreeCAD 1.x (propiedad `Class` en lugar de `IfcType`, elementos sin desplegar) y concluía erróneamente "plano 2D". Ahora lee el IFC en memoria (o desde su ruta) con IfcOpenShell.
- Si no reconoce ningún objeto devuelve `NO RECONOCIDO` con un bloque de diagnóstico (TypeId y clases), en lugar de suponer que es 2D.
- `SKILL.md`: instrucciones para el modo IFC nativo y para el caso `NO RECONOCIDO`.

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
