# cte-db-si-freecad

**Skill para asistentes de IA (Claude, ChatGPT y otros compatibles con `SKILL.md`) que verifica el cumplimiento del CTE DB-SI — Seguridad en caso de incendio — sobre modelos de FreeCAD (vía MCP) o archivos IFC.**

El asistente extrae del modelo los parámetros relevantes (plantas y cotas, recintos, superficies, puertas, pasillos, escaleras, muros, equipos PCI…), los contrasta con las exigencias de las secciones **SI 1 a SI 6** y emite un informe con cada comprobación marcada como `CUMPLE`, `NO CUMPLE`, `NO VERIFICABLE` o `NO APLICA`, citando apartado y tabla.

> [!WARNING]
> Herramienta de **ayuda técnica orientativa**. No sustituye la justificación del técnico competente, el visado ni la licencia. Las cifras proceden del **texto consolidado del DB-SI de 4 de marzo de 2025**, que no tiene valor jurídico. Comprueba siempre la versión vigente y la normativa autonómica y municipal aplicable.

---

## Qué incluye

| Bloque | Contenido |
|---|---|
| **SI 1** Propagación interior | Sectores (tabla 1.1), resistencia de elementos delimitadores (1.2), locales de riesgo especial (2.1 y 2.2), espacios ocultos, reacción al fuego (4.1) |
| **SI 2** Propagación exterior | Medianerías, distancias entre fachadas según ángulo, franjas, reacción al fuego de fachadas y cubiertas |
| **SI 3** Evacuación | Ocupación (tabla 2.1), número de salidas y recorridos (3.1), dimensionado (4.1 y 4.2), protección de escaleras (5.1), puertas, señalización, control de humo, personas con discapacidad |
| **SI 4** Instalaciones PCI | Dotación por uso (tabla 1.1): extintores, BIE, columna seca, detección, alarma, hidrantes, extinción automática |
| **SI 5** Bomberos | Viales de aproximación, espacio de maniobra, huecos de fachada |
| **SI 6** Estructura | Resistencias R (tablas 3.1 y 3.2), tablas de hormigón (anejo C), madera (anejo E), fábricas (anejo F), tiempo equivalente (anejo B) |
| **Anejo SI A** | Definiciones clave: altura de evacuación, origen de evacuación, salida de planta, escalera protegida… |
| **Scripts** | Extracción desde FreeCAD y lectura directa de IFC, con un **control de calidad del modelo** previo |

## Estructura del repositorio

```
cte-db-si-freecad/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── docs/
│   ├── instalacion-claude.md
│   ├── instalacion-chatgpt.md
│   ├── freecad-mcp.md
│   └── flujo-de-trabajo.md
└── cte-db-si-freecad/            ← ESTA carpeta es el skill (es lo que se instala)
    ├── SKILL.md                  ← instrucciones, tablas y criterios del DB-SI
    └── scripts/
        ├── freecad_extraer.py    ← extracción desde el documento activo de FreeCAD
        ├── ifc_extraer.py        ← extracción directa de un .ifc (IfcOpenShell)
        └── ifc_planta.py         ← dibuja la planta de un .ifc para revisarla
```

## Descarga e instalación rápida

1. Ve a **[Releases](https://github.com/wmunny/cte-db-si-freecad/releases)** y descarga `cte-db-si-freecad.zip` (contiene sólo la carpeta del skill).
   Alternativa: botón **Code → Download ZIP** y usa la carpeta interior `cte-db-si-freecad/`.
2. Instálalo en tu asistente:
   - **Claude** (app web/escritorio, Claude Code): ver [docs/instalacion-claude.md](docs/instalacion-claude.md)
   - **ChatGPT** (web/escritorio): ver [docs/instalacion-chatgpt.md](docs/instalacion-chatgpt.md)
3. Para trabajar sobre FreeCAD, conecta un servidor MCP de FreeCAD: ver [docs/freecad-mcp.md](docs/freecad-mcp.md).
   Para verificar un **.ifc** no hace falta FreeCAD.

## Uso

Con el skill instalado, basta con pedirlo en lenguaje natural:

- *"Comprueba si el modelo abierto en FreeCAD cumple el DB-SI."*
- *"Verifica la evacuación de la planta baja de este IFC."* (adjuntando el archivo)
- *"¿Las puertas de este proyecto cumplen la tabla 4.1 de SI 3?"*

El asistente empezará mostrando el **control de calidad del modelo** (qué datos tiene y cuáles faltan), te preguntará lo que no esté en el modelo (uso, extinción automática, clases de reacción/resistencia…) y después emitirá el informe.

Los scripts también se pueden usar solos:

```bash
pip install ifcopenshell numpy matplotlib
python cte-db-si-freecad/scripts/ifc_extraer.py modelo.ifc          # resumen + calidad
python cte-db-si-freecad/scripts/ifc_extraer.py modelo.ifc --json   # datos completos
python cte-db-si-freecad/scripts/ifc_planta.py  modelo.ifc planta.png
```

Más detalle del flujo recomendado (FCStd vs IFC vs DXF) en [docs/flujo-de-trabajo.md](docs/flujo-de-trabajo.md).

## Para obtener buenos resultados

El resultado depende de la calidad del modelo. Lo que más mejora la verificación:

- **Espacios** (`Arch Space` en FreeCAD / `IfcSpace` en IFC) con nombre o uso.
- **Plantas** (`Building Storey`) con su cota.
- **Uso del edificio** declarado.
- **Anchura libre de paso** de las puertas (no sólo la nominal).
- Propiedades de incendio cuando se conozcan: `FireRating`, `FireExit`, materiales.

## Fuente normativa

- Documento Básico SI — Seguridad en caso de incendio, CTE. Texto consolidado de **4 de marzo de 2025** (incluye RD 164/2025, BOE 10/04/2025).
  Descarga oficial: <https://www.codigotecnico.org/pdf/Documentos/SI/DBSI.pdf>

Cada cifra del `SKILL.md` se ha contrastado con ese documento. Las figuras del DB-SI no están digitalizadas (las reglas que ilustran sí están en el texto); las isotermas del anejo C y la tabla D.1 completa del anejo D no se incluyen.

## Limitaciones conocidas

- La anchura mínima de escaleras está en el **DB SUA** (fuera de este skill).
- Estructuras de acero (anejo D): requieren datos de cálculo; quedan como `NO VERIFICABLE` salvo protección certificada.
- Los recorridos de evacuación sin trazado explícito se **estiman** (cota inferior euclídea / superior "Manhattan").
- `freecad_extraer.py` está comprobado en sintaxis; las propiedades de los objetos BIM pueden variar entre versiones de FreeCAD. `ifc_extraer.py` está probado con modelos IFC4 reales.

## Contribuir

Se agradecen issues y pull requests: errores en cifras (indicando apartado y tabla del DB-SI), mejoras de los scripts, compatibilidad con otros MCP de FreeCAD o con nuevas versiones del DB-SI. Cuando cambie el DB-SI, actualiza `SKILL.md`, indica la nueva versión en la cabecera y en `CHANGELOG.md`.

## Licencia

[MIT](LICENSE). El contenido normativo procede del Código Técnico de la Edificación, disposición publicada en el BOE (art. 13 de la Ley de Propiedad Intelectual: las disposiciones legales y reglamentarias no son objeto de propiedad intelectual).
