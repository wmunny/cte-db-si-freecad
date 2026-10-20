---
name: cte-db-si-freecad
description: Verifica si un modelo de FreeCAD (vía MCP) o un archivo IFC cumple el CTE DB-SI (seguridad en caso de incendio, SI 1 a SI 6): extrae parámetros, los contrasta y emite informe.
---

# Verificación CTE DB-SI sobre modelos FreeCAD (vía MCP) o archivos IFC

Fuente normativa: **CTE Documento Básico SI, texto consolidado de 4 de marzo de 2025** (incluye RD 164/2025, BOE 10/04/2025). Todas las cifras de este skill están transcritas de ese documento. El texto consolidado no tiene valor jurídico; el informe debe decirlo.

Úsalo cuando el usuario pida comprobar si un plano/modelo cumple el CTE, el DB-SI, "normativa de incendios", sectorización, evacuación, anchos de puertas/escaleras, recorridos, ocupación, resistencia al fuego, etc., sobre un documento accesible por un MCP de FreeCAD o sobre un archivo IFC.

## 0. Principios

1. **Nunca inventes datos del proyecto.** Cada dato usado lleva su origen: `MODELO` (leído de FreeCAD o del IFC), `USUARIO` (lo ha dicho), `SUPUESTO` (hipótesis explícita, conservadora). Si un dato crítico falta, pregúntalo o marca la comprobación como `NO VERIFICABLE`.
2. **Un plano no contiene todo.** Reacción al fuego, clasificación EI/REI de productos, potencias de instalaciones, carga de fuego, existencia de rociadores, etc. normalmente NO están en la geometría. Pídelos o déjalos como `NO VERIFICABLE`.
3. **Resultado por comprobación:** `CUMPLE` · `NO CUMPLE` · `NO VERIFICABLE` (falta dato) · `NO APLICA`. Cita siempre el apartado y la tabla (p. ej. "SI 3, tabla 4.1").
4. **Ámbito:** el DB-SI **no** se aplica a edificios/establecimientos/zonas de uso industrial sujetos al RSCIEI. Uso Almacén: SI 1 tabla 1.1 + anexos I-IV del RSCIEI (ocupación con SI 3 tabla 2.1, 40 m²/pers).
5. **Unidades:** FreeCAD trabaja internamente en **mm** (longitudes) y **mm²** (áreas); un IFC declara sus propias unidades (los scripts ya convierten). Convierte siempre a m y m² antes de comparar. En un IFC, `OverallWidth` de una puerta es la anchura **nominal**, no la libre de paso.
6. El informe es una **ayuda técnica**, no sustituye la justificación del proyectista ni el visado/licencia.

## 1. Flujo de trabajo

0. **Elegir la fuente de datos y comprobar su calidad** (antes de cualquier comprobación):
   - **Original en FreeCAD (.FCStd)** con un MCP conectado → trabajar sobre el modelo vivo. Ejecuta `scripts/freecad_extraer.py` con la herramienta de ejecución de código del MCP (si el skill no trae la carpeta `scripts/`, usa los fragmentos de la sección 2).
   - **Archivo .ifc** (sin FreeCAD o como entregable) → leerlo directamente con IfcOpenShell: `python scripts/ifc_extraer.py modelo.ifc` (o `--json`). `scripts/ifc_planta.py modelo.ifc planta.png` dibuja la planta para revisarla. Requiere `pip install ifcopenshell numpy matplotlib`. No hace falta pasar por FreeCAD sólo para verificar.
   - **Plano 2D** (DXF, Draft, Sketch): avisa de que la verificación será muy aproximada y recomienda convertirlo antes a BIM (muros, puertas, espacios).
   - **IFC abierto en FreeCAD en modo nativo** (FreeCAD 1.x, banco BIM): los objetos usan la propiedad `Class` ("IfcWall") en vez de `IfcType` y los elementos pueden no estar desplegados en el árbol. `freecad_extraer.py` lo detecta y lee el IFC con IfcOpenShell (incluido en FreeCAD). Si usas los fragmentos de la sección 2, busca también `Class` y no concluyas "2D" sólo porque no aparezcan objetos Arch.
   - Si el script devuelve `NO RECONOCIDO`, **no supongas que es un plano 2D**: muestra el bloque `diagnostico` (TypeId y clases) y pregunta al usuario cómo se creó o abrió el modelo.
   - Ambos scripts devuelven un bloque **CALIDAD** (plantas, espacios, uso declarado, puertas, FireRating, estructura, materiales, cabecera "provisional"). **Muéstralo al usuario al principio**, explica qué comprobaciones quedarán como `NO VERIFICABLE` por cada carencia y pregunta si quiere completar el modelo o seguir con supuestos.
   - Flujo recomendado: verificar → corregir en FreeCAD (MCP o a mano) → volver a verificar → exportar IFC como entregable (opcionalmente verificarlo también como contraste).
1. **Inspeccionar el MCP** (si se trabaja en FreeCAD): lista los documentos y objetos con las herramientas disponibles (típicamente `list_documents`, `get_objects`, `get_object`, `get_view`, `execute_code`). Si existe `execute_code` (ejecutar Python dentro de FreeCAD), usa los scripts de la sección 2; es la vía más fiable. Toma una captura con `get_view` si existe para orientarte.
2. **Identificar el tipo de modelo**:
   - *BIM (Arch/BIM, IFC importado)*: hay `Arch Space`, `Arch Wall`, `Arch Window` (puertas con `IfcType`="Door"), `Arch Stairs`, `BuildingPart`/plantas (`IfcType`="Building Storey").
   - *2D (DXF/DWG importado, Draft/Sketch)*: líneas, polilíneas, textos y capas. Habrá que inferir recintos (polilíneas cerradas) y anchos (cotas o distancias entre líneas) → más datos `SUPUESTO`/`USUARIO`.
3. **Recoger datos de partida** (tabla de la sección 3). Pregunta al usuario de una sola vez lo que falte y sea crítico: uso principal y usos subsidiarios, obra nueva / reforma / cambio de uso, existencia de instalación automática de extinción, si algún espacio es "aire libre", clases de reacción/resistencia previstas.
4. **Calcular magnitudes derivadas**: altura de evacuación (desc./asc.), superficies construidas por sector, superficies útiles por recinto, ocupación (SI 3-2), asignación de ocupantes a salidas (SI 3-4.1).
5. **Ejecutar las comprobaciones** SI 1 → SI 6 (secciones 5 a 10).
6. **Emitir el informe** con el formato de la sección 12.

## 2. Extracción de datos desde FreeCAD (`execute_code`)

Ejecuta estos scripts adaptándolos al documento. Son de solo lectura; **no modifiques el modelo** salvo que el usuario lo pida (p. ej. dibujar un recorrido de evacuación).

### 2.1 Inventario general
```python
import FreeCAD as App
doc = App.ActiveDocument
from collections import Counter
c = Counter()
for o in doc.Objects:
    t = getattr(o, "IfcType", None) or getattr(o, "IfcRole", None) or o.TypeId
    c[str(t)] += 1
print("DOC:", doc.Name, "| objetos:", len(doc.Objects))
for k, v in c.most_common(): print(f"{v:5d}  {k}")
```

### 2.2 Plantas / niveles (para altura de evacuación)
```python
import FreeCAD as App
doc = App.ActiveDocument
for o in doc.Objects:
    if getattr(o, "IfcType", "") in ("Building Storey",) or o.TypeId.endswith("Floor"):
        z = o.Placement.Base.z / 1000.0
        h = getattr(o, "Height", 0)
        h = float(h) / 1000.0 if h else None
        print(f"{o.Label!r}: cota z = {z:.2f} m, altura = {h}")
```

### 2.3 Espacios / recintos (superficie, uso, ocupación declarada)
```python
import FreeCAD as App
doc = App.ActiveDocument
for o in doc.Objects:
    if hasattr(o, "Area") and (getattr(o, "IfcType", "") == "Space" or o.Name.startswith("Space")):
        a = float(o.Area) / 1e6  # mm2 -> m2
        planta = next((p.Label for p in o.InList if getattr(p, "IfcType", "") == "Building Storey"), "?")
        print(f"{o.Label!r} | planta {planta} | A = {a:.2f} m2 | SpaceType={getattr(o,'SpaceType','')} "
              f"| Personas={getattr(o,'NumberOfPeople','')} | Desc={getattr(o,'Description','')}")
```
Si no hay `Arch Space`, busca caras/polilíneas cerradas: `o.Shape.Area` de objetos con `Shape.isClosed()` o `Shape.Faces`, y los textos cercanos (`Draft Text`/`Text` → `o.Text`) para identificar el uso.

### 2.4 Puertas (anchura de paso)
```python
import FreeCAD as App
doc = App.ActiveDocument
for o in doc.Objects:
    if getattr(o, "IfcType", "") == "Door" or (hasattr(o, "Width") and "door" in (o.Label + str(getattr(o, "Preset", ""))).lower()):
        w = float(o.Width) / 1000.0
        hojas = 2 if "Double" in str(getattr(o, "WindowParts", "")) or "Double" in o.Label else 1
        host = [h.Label for h in getattr(o, "Hosts", [])]
        print(f"{o.Label!r}: ancho total = {w:.3f} m | hojas~{hojas} | muro: {host} | "
              f"pos = {tuple(round(v/1000,2) for v in o.Placement.Base)} m")
```
Anchura de cálculo = anchura libre de paso. Si sólo se conoce la anchura de hueco/marco, márcalo `SUPUESTO` y avisa de que la anchura libre es menor (descuento de marco y hoja).

### 2.5 Muros (espesor, para tablas F.1/F.2 y compartimentación)
```python
import FreeCAD as App
doc = App.ActiveDocument
for o in doc.Objects:
    if getattr(o, "IfcType", "") == "Wall":
        print(f"{o.Label!r}: e = {float(o.Width):.0f} mm | h = {float(o.Height)/1000:.2f} m | "
              f"L = {float(getattr(o,'Length',0))/1000:.2f} m | material = {getattr(getattr(o,'Material',None),'Label','')}")
```

### 2.6 Escaleras
```python
import FreeCAD as App
doc = App.ActiveDocument
for o in doc.Objects:
    if getattr(o, "IfcType", "") in ("Stair", "Stair Flight") or o.TypeId.endswith("Stairs"):
        print(f"{o.Label!r}: ancho = {float(o.Width)/1000:.2f} m | altura salvada = {float(o.Height)/1000:.2f} m | "
              f"peldaños = {getattr(o,'NumberOfSteps','?')}")
```

### 2.7 Recorridos de evacuación
La longitud se mide **sobre el eje** de pasillos, escaleras y rampas (Anejo SI A). Orden de preferencia:
1. **Trazado explícito**: pide al usuario (o propón dibujar, con permiso) una `Draft Wire` por recorrido en una capa/grupo "EVACUACION" y mide `o.Shape.Length/1000`.
2. **Estimación por cotas**: desde el origen más desfavorable hasta la salida.
   - Distancia euclídea `d_e` = cota inferior de la longitud real. Si `d_e` > límite → **NO CUMPLE** con seguridad.
   - Distancia "Manhattan" `d_m` (|Δx|+|Δy|) suele ser una cota superior en plantas ortogonales. Si `d_m` ≤ límite → **CUMPLE (estimado)**.
   - Si `d_e` ≤ límite < `d_m` → **NO VERIFICABLE** hasta trazar el recorrido.
```python
import FreeCAD as App
p0 = App.Vector(x0, y0, 0); p1 = App.Vector(x1, y1, 0)   # mm
de = (p1 - p0).Length / 1000; dm = (abs(p1.x-p0.x) + abs(p1.y-p0.y)) / 1000
print(f"euclidea {de:.2f} m | manhattan {dm:.2f} m")
```
Recuerda: el **origen de evacuación** es todo punto ocupable, excepto el interior de viviendas y recintos (o conjuntos comunicados) con densidad ≤ 1 pers/5 m² y superficie total ≤ 50 m² (habitaciones de hotel, despachos…): en esos el recorrido empieza en su puerta. Locales de riesgo especial y zonas de ocupación nula > 50 m² sí son origen.

## 3. Datos de partida necesarios

| Dato | Fuente habitual | Uso en |
|---|---|---|
| Uso principal del edificio/establecimiento y usos subsidiarios | USUARIO / textos del plano | todo |
| Tipo de obra (nueva, reforma con/sin cambio de uso, cambio de uso parcial) | USUARIO | ámbito (Intro III) |
| Cotas de cada planta y de la(s) salida(s) de edificio | MODELO | altura de evacuación |
| Superficie construida por planta, sector y establecimiento | MODELO | SI 1, SI 4 |
| Superficie útil y uso de cada recinto | MODELO | ocupación SI 3-2 |
| Puertas: anchura libre, nº hojas, sentido de giro, tipo | MODELO + USUARIO | SI 3-4, SI 3-6 |
| Pasillos: anchura libre | MODELO (cotas) | SI 3-4 |
| Escaleras: anchura, altura salvada, protección, accesos | MODELO + USUARIO | SI 3-4, SI 3-5 |
| Locales de riesgo especial: tipo, S, V, potencia | MODELO + USUARIO | SI 1-2 |
| Instalación automática de extinción (sí/no, zonas) | USUARIO | duplica superficies, +25 % recorridos |
| Clases de reacción al fuego de revestimientos y fachada | USUARIO | SI 1-4, SI 2 |
| EI/REI de cerramientos, forjados y puertas; espesores y tipo de fábrica | USUARIO / MODELO (espesor) | SI 1, SI 6, Anejo F |
| Entorno: viales, espacio de maniobra, huecos de fachada | MODELO (planta de emplazamiento) | SI 5 |

## 4. Definiciones clave (Anejo SI A) para interpretar el plano

- **Altura de evacuación**: máxima diferencia de cotas entre un origen de evacuación y la salida de edificio que le corresponda. No se consideran las plantas más altas con sólo zonas de ocupación nula.
- **Salida de planta**: (1) arranque de escalera compartimentada como sector, o puerta de acceso a escalera protegida, pasillo protegido o vestíbulo de independencia de escalera especialmente protegida (desde hospitalización/tratamiento intensivo: ≥ 0,70 / 1,50 m² por ocupante); (2) puerta, a través de vestíbulo de independencia, a otro sector de la misma planta si: el sector inicial tiene otra salida de planta que no lleve al mismo sector; el sector alternativo tiene en zonas de circulación 0,5 m²/pers para los ocupantes del inicial (sólo puntos a < 30 m de recorrido del acceso); y su evacuación no confluye con la del inicial salvo en sector de riesgo mínimo; (3) una salida de edificio.
- **Salida de edificio**: puerta o hueco a espacio exterior seguro. Para ≤ 500 personas vale la que da a un espacio exterior con dos recorridos alternativos a dos espacios exteriores seguros, uno de ellos ≤ 50 m.
- **Espacio exterior seguro**: delante de cada salida, superficie ≥ 0,5·P m² dentro de un radio 0,1·P m (no comprobar si P ≤ 50). Si no comunica con la red viaria u otros espacios abiertos, no cuenta la zona a < 15 m del edificio (salvo sectores estructuralmente independientes). Cubierta sólo si su estructura es independiente del edificio que evacua a ella.
- **Recorridos alternativos**: forman en el punto un ángulo > 45º o están separados por elementos EI 30 que impidan su bloqueo simultáneo por humo.
- **Recorrido de evacuación**: no valen escaleras mecánicas ni pasos con tornos. Rampas y pasillos móviles sí valen si no pueden usarse con carros y tienen dispositivo de parada manual o automático (por detección y alarma). Los recorridos desde zonas habitables o aparcamiento **no pueden atravesar zonas de riesgo especial**. Desde zonas habitables sólo pueden atravesar aparcamiento (o sus vestíbulos) si es recorrido alternativo. En aparcamiento discurren por calles de circulación o itinerarios peatonales protegidos (DB SUA 7). En Comercial con > 400 m² para público: salvo los 10 primeros metros, por pasillos definidos en proyecto con tramos ≤ 20 m entre transversales. Cajas de cobro con carros: no son elementos de evacuación; salidas intercaladas con ≤ 10 cajas entre salidas (< 10 cajas: 2 salidas en extremos; < 5 cajas: 1 salida en extremo). Sin carros: pasos por cajas válidos si ancho libre ≥ 0,70 m.
- **Máxima altura salvada en sentido ascendente** (no aplica a aparcamientos, zonas de ocupación nula ni personal de mantenimiento): en general 4 m hasta salida de planta y 6 m hasta espacio exterior seguro; hospitalización/tratamiento intensivo y docente infantil/primaria: 1 m y 2 m (sin límite en tratamiento intensivo con radioterapia).
- **Sector bajo rasante**: el que exige salvar una altura de evacuación ascendente ≥ 1,5 m.
- **Sector de riesgo mínimo**: sólo circulación, no bajo rasante; carga de fuego ≤ 40 MJ/m² en el sector y ≤ 50 MJ/m² en cualquier recinto; separado por EI 120 con vestíbulos de independencia; evacuación por salidas de edificio directas a espacio exterior seguro.
- **Escalera protegida**: trazado continuo hasta planta de salida; recinto exclusivo de circulación con separadores EI 120; ≤ 2 accesos por planta mediante puertas EI2 60-C5 desde circulaciones comunes sin ocupación propia (pueden abrir aseos y ascensores; registros EI 60); en planta de salida, recorrido desde la puerta de la escalera hasta salida de edificio ≤ 15 m (salvo por sector de riesgo mínimo); protección frente al humo: (a) ventanas/huecos ≥ 1 m² útil por planta, o (b) dos conductos independientes con 50 cm²/m³ de recinto por planta (relación lados ≤ 4; rejillas de entrada con borde superior < 1 m y de salida enfrentadas con borde inferior > 1,80 m), o (c) presión diferencial EN 12101-6.
- **Escalera especialmente protegida**: protegida + vestíbulo de independencia diferente en cada acceso (no necesario si es abierta al exterior, ni en planta de salida en ascendente). **Escalera abierta al exterior**: huecos permanentes ≥ 5·A m² por planta (A = ancho de tramo); si da a patio, círculo inscrito de diámetro h/3.
- **Pasillo protegido**: condiciones equivalentes a escalera protegida; ventilación por huecos ≥ 0,2·L m²; con conductos, rejillas de entrada < 1 m en un paramento y de salida > 1,80 m en el otro, separadas ≤ 10 m; trazado continuo hasta escalera protegida, sector de riesgo mínimo o salida de edificio.
- **Vestíbulo de independencia**: paredes EI 120; puertas con 1/4 de la resistencia del elemento compartimentador y ≥ EI2 30-C5; distancia entre barridos de puertas ≥ 0,50 m; en itinerario accesible círculo Ø 1,20 m libre (Ø 1,50 m si contiene zona de refugio); mecanismos de apertura ≥ 0,30 m del rincón. Si sirve a locales de riesgo especial no puede usarse en recorridos de zonas habitables.
- **Zona de refugio**: plazas de 1,20 × 0,80 m (silla de ruedas) o 0,80 × 0,60 m (otra movilidad reducida), en rellanos de escaleras protegidas/especialmente protegidas, vestíbulos de éstas o pasillo protegido, sin invadir el ancho libre; círculo Ø 1,50 m junto a ella; intercomunicador si hay puesto de control (no residencial vivienda).
- **Aparcamiento abierto**: en cada planta, aberturas permanentes ≥ 1/20 de la superficie construida, de ellas ≥ 1/40 repartida entre las dos paredes opuestas más próximas; borde superior de aberturas a ≤ 0,5 m del techo.
- **Ascensor de emergencia**: acceso desde escalera protegida o vestíbulo de especialmente protegida con puerta E30; ≥ 630 kg, cabina 1,10 × 1,40 m (hospitalario 1,20 × 2,10 m), paso 1,00 m, recorrido total < 60 s; pulsador "USO EXCLUSIVO BOMBEROS"; fuente propia ≥ 1 h; uno por cada 1000 ocupantes o fracción.
- **Uso Aparcamiento**: > 100 m² construidos (excluye garaje de vivienda unifamiliar y aparcamientos exteriores aunque estén cubiertos). Robotizados: sin ocupación ni exigencias de evacuación.
- **Asimilaciones (Intro III)**: residencias geriátricas, de discapacitados, educación especial → **Hospitalario**; sanitario/asistencial ambulatorio → **Administrativo**; uso no listado → el más asimilable. Superficie útil comercial sin implantación definida: ≥ 75 % de la construida de zonas de público. Alquiler de trasteros y almacenes → uso Almacén, NRI medio subnivel 5 si la altura de almacenamiento es ≤ 3 m y NRI alto (subnivel según RSCIEI) si es > 3 m. Áreas públicas de venta comerciales y archivos abiertos en oficinas no son uso Almacén, salvo QT ≥ 3·10⁶ MJ con almacenamiento > 5,00 m (entonces se añaden las exigencias del RSCIEI más estrictas).

## 5. SI 1 — Propagación interior

### 5.1 Sectores de incendio (tabla 1.1)
Superficies máximas **duplicables con instalación automática de extinción**. No computan en la superficie del sector: locales de riesgo especial, escaleras y pasillos protegidos, vestíbulos de independencia y escaleras compartimentadas como sector contenidos en él. Sin límite para sectores de riesgo mínimo.

**En general**:
- Todo establecimiento = sector diferenciado del resto del edificio, salvo en edificios de uso principal Residencial Vivienda los establecimientos ≤ 500 m² de uso Docente, Administrativo o Residencial Público.
- Zona de uso distinto y subsidiario del principal = sector diferente si supera: Residencial Vivienda → siempre; alojamiento o Administrativo/Comercial/Docente → > 500 m² (> 250 m² si principal Almacén); Pública concurrencia → > 500 personas (o > 250 m² si principal Almacén); Aparcamiento → > 100 m² (comunicación con otros usos por vestíbulo de independencia); varios usos anteriores en conjunto > 250 m² con principal Almacén; Almacén con QT ≥ 3·10⁶ MJ.
- Espacio diáfano: puede ser sector único mayor si ≥ 90 % en una planta, salidas directas al exterior, ≥ 75 % del perímetro es fachada y sin zona habitable encima.

| Uso | Superficie construida máx. del sector y condiciones |
|---|---|
| Residencial Vivienda | 2.500 m²; elementos entre viviendas ≥ EI 60 |
| Administrativo | 2.500 m² |
| Comercial | 2.500 m² en general; 10.000 m² si ocupa todo el edificio, con extinción automática y h_evac ≤ 10 m. Edificio exento con extinción: zonas de público sector único si h_evac desc ≤ 10 m, asc ≤ 4 m y cada planta evacua por salidas de edificio propias y salidas a escaleras/pasillos protegidos directos al exterior. Elementos entre establecimientos EI 60 (no frente a zonas comunes). En centros comerciales, establecimientos de Pública concurrencia con espectáculos (cualquier S) o > 500 m² (otra actividad) = sector propio |
| Residencial Público | 2.500 m²; habitaciones y oficios de planta: paredes EI 60 y, en establecimientos > 500 m², puertas EI2 30-C5 |
| Docente | > 1 planta: 4.000 m²; 1 planta: no requiere sectorizar |
| Hospitalario | Plantas con hospitalización o unidades especiales: ≥ 2 sectores ≤ 1.500 m² cada uno, capaces de albergar pacientes de un sector contiguo (excepto plantas ≤ 1.500 m² con salidas directas a espacio exterior seguro y recorridos ≤ 25 m). Resto: 2.500 m² |
| Pública concurrencia | 2.500 m². Público sentado en asientos fijos, museos, culto, polideportivos, feriales: puede superarse si EI 120 frente a otras zonas, salidas a sector de riesgo mínimo por vestíbulo o salidas de edificio, revestimientos B-s1,d0 paredes/techos y BFL-s1 suelos, carga de fuego de revestimientos y mobiliario fijo ≤ 200 MJ/m², sin zona habitable encima. Cajas escénicas = sector propio |
| Aparcamiento | Sector propio si está integrado con otros usos; comunicación por vestíbulo de independencia. Robotizados bajo otro uso: sectores ≤ 10.000 m³ |

**Ascensores/escaleras entre sectores** (SI 1-1.4): compartimentados como el sector. Ascensores: en cada acceso puertas E 30 o vestíbulo de independencia con puerta EI2 30-C5; en riesgo especial o Aparcamiento siempre vestíbulo. Entre dos sectores, si el inferior es de riesgo mínimo, o si en él se disponen a la vez la puerta EI2 30-C5 del vestíbulo y la puerta E 30 del ascensor, el sector superior no necesita ninguna de esas medidas.

**Caja escénica** (Anejo A): EI 120 respecto de la sala salvo la boca de escena, cerrable con telón EI 60 incombustible que cierre en ≤ 30 s y resista 0,4 kN/m² en ambos sentidos (cierre automático y manual desde dos puntos, señal óptica, cortina de agua); vestíbulos de independencia en toda comunicación con la sala; sobre la escena sólo locales técnicos propios; recorrido desde cualquier punto del escenario hasta salida del sector ≤ 25 m con puertas que abren en sentido de evacuación; pasarelas y galerías con salidas; pasarelas y escaleras del escenario ≥ 0,80 m; eliminación de humo en la parte superior.

### 5.2 Resistencia al fuego de elementos delimitadores de sector (tabla 1.2)

| Paredes y techos que separan el sector, uso | Bajo rasante | h ≤ 15 m | 15 < h ≤ 28 m | h > 28 m |
|---|---|---|---|---|
| Sector de riesgo mínimo | no se admite | EI 120 | EI 120 | EI 120 |
| Res. Vivienda, Res. Público, Docente, Administrativo | EI 120 | EI 60 | EI 90 | EI 120 |
| Comercial, Pública concurrencia, Hospitalario | EI 120 (EI 180 si h > 28 m) | EI 90 | EI 120 | EI 180 |
| Aparcamiento | EI 120 (EI 180 robotizado) | EI 120 | EI 120 | EI 120 |

h = altura de evacuación del edificio. Techos sobre otra planta: REI (no EI). Cubierta no transitable ni de evacuación: sólo R estructural (salvo franjas de SI 2). Resistencia del suelo según uso de la planta inferior (SI 6). Alternativa: tiempo equivalente (Anejo B).
**Puertas entre sectores**: EI2 t-C5 con t = 1/2 del tiempo exigido a la pared, o 1/4 si el paso es por vestíbulo de independencia con dos puertas.

### 5.3 Locales y zonas de riesgo especial (tabla 2.1) — Bajo / Medio / Alto

| Local | Bajo | Medio | Alto |
|---|---|---|---|
| Talleres de mantenimiento, almacenes de combustibles (mobiliario, lencería, limpieza), archivos, depósitos de libros | 100<V≤200 m³ | 200<V≤400 m³ | V>400 m³ |
| Almacén de residuos | 5<S≤15 m² | 15<S≤30 m² | S>30 m² |
| Aparcamiento S ≤ 100 m² o en vivienda unifamiliar | en todo caso | | |
| Cocinas, potencia P | 20<P≤30 kW | 30<P≤50 kW | P>50 kW |
| Lavanderías, vestuarios de personal, camerinos (aseos no computan) | 20<S≤100 m² | 100<S≤200 m² | S>200 m² |
| Salas de calderas, P útil nominal | 70<P≤200 kW | 200<P≤600 kW | P>600 kW |
| Salas de máquinas de climatización (RITE) | en todo caso | | |
| Maquinaria frigorífica: amoniaco | | | en todo caso |
| Maquinaria frigorífica: halogenado | P≤400 kW | P>400 kW | |
| Almacén combustible sólido calefacción | S≤3 m² | S>3 m² | |
| Contadores de electricidad y cuadros generales | en todo caso | | |
| Centro de transformación, dieléctrico seco o con punto de inflamación > 300 ºC | en todo caso | | |
| CT, dieléctrico con p. inflamación ≤ 300 ºC (total / por transformador) | P<2.520 kVA / P<630 kVA | 2.520<P<4.000 / 630<P<1.000 kVA | P>4.000 / P>1.000 kVA |
| Sala de maquinaria de ascensores | en todo caso | | |
| Grupo electrógeno | en todo caso | | |
| Res. Vivienda: trasteros | 50<S≤100 m² | 100<S≤500 m² | S>500 m² |
| Hospitalario: almacenes farmacéuticos y clínicos | 100<V≤200 m³ | 200<V≤400 m³ | V>400 m³ |
| Hospitalario: esterilización y almacenes anejos | | | en todo caso |
| Hospitalario: laboratorios clínicos | V≤350 m³ | 350<V≤500 m³ | V>500 m³ |
| Administrativo: imprenta, reprografía y anejos | 100<V≤200 m³ | 200<V≤500 m³ | V>500 m³ |
| Res. Público: roperos y consignas | S≤20 m² | 20<S≤100 m² | S>100 m² |
| Comercial: almacenes según QS | 425<QS≤850 MJ/m² | 850<QS≤3.400 MJ/m² | QS>3.400 MJ/m² |
| Pública concurrencia: taller o almacén de decorados/vestuario | | 100<V≤200 m³ | V>200 m³ |

Notas: cocinas — sólo aparatos de preparación de alimentos susceptibles de ignición; freidoras y sartenes basculantes a 1 kW/litro; fuera de Hospitalario y Res. Público no son riesgo especial si tienen extinción automática (obligatoria > 50 kW). Extracción de cocinas de riesgo especial: campanas a ≥ 50 cm de materiales no A1; conductos exclusivos con registros en cambios de dirección > 30º y cada ≤ 3 m horizontales; EI 30 en interior o a < 1,50 m de fachada no EI 30/huecos; sin compuertas cortafuego; filtros a > 1,20 m (parrilla/gas) o > 0,50 m, inclinación > 45º, bandeja a recipiente < 3 l; ventiladores F 400 90. Locales de la nota (1) y (6) con > 500 m³ (nota 1) y QT ≥ 3·10⁶ MJ = uso Almacén. Comercial — superficie máxima de almacenes clasificados: sobre planta de salida, con extinción S<2.000 / <600 / <25 m² (alto sólo con h_evac < 15 m); sin extinción S<1.000 / <300 m² / no se admite; bajo planta de salida, con extinción <800 m² / no / no; sin extinción <400 m² / no / no. Áreas públicas de venta no son riesgo especial. Equipos en cubierta quedan excluidos.

**Condiciones (tabla 2.2)**

| Característica | Bajo | Medio | Alto |
|---|---|---|---|
| Estructura portante | R 90 | R 120 | R 180 |
| Paredes y techos que separan la zona | EI 90 | EI 120 | EI 180 |
| Vestíbulo de independencia en cada comunicación | – | Sí | Sí |
| Puertas de comunicación | EI2 45-C5 | 2 × EI2 30-C5 | 2 × EI2 45-C5 |
| Máximo recorrido hasta alguna salida del local | 25 m | 25 m | 25 m |

+25 % de recorrido con extinción automática. El recorrido interior computa en el total hasta la salida de planta (no limitado desde garaje de unifamiliar hasta salida de la vivienda). Resistencia no menor que la del sector al que sirve (tabla 1.2), salvo bajo cubierta no evacuable sin riesgo para otras plantas: R 30.

### 5.4 Espacios ocultos y pasos de instalaciones (SI 1-3)
Continuidad de la compartimentación en patinillos, cámaras, falsos techos y suelos elevados (registros de mantenimiento: mitad de resistencia). Penetraciones > 50 cm²: compuerta EI t (i↔o) o dispositivo intumescente, o elementos pasantes EI t (i↔o).

### 5.5 Reacción al fuego (tabla 4.1) — revestimientos (> 5 % de paredes, techos o suelos del recinto)

| Situación | Techos y paredes | Suelos |
|---|---|---|
| Zonas ocupables (excluye interior de viviendas; Hospitalario como protegidos) | C-s2,d0 | EFL |
| Pasillos y escaleras protegidos | B-s1,d0 | CFL-s1 |
| Aparcamientos y recintos de riesgo especial | B-s1,d0 | BFL-s1 |
| Espacios ocultos no estancos (patinillos, falsos techos, suelos elevados, salvo dentro de viviendas) o estancos con instalaciones | B-s3,d0 | BFL-s2 |

Incluye tuberías y conductos sin recubrimiento resistente (aislamiento lineal: subíndice L) y capas interiores no protegidas por capa EI 30. Carpas: T2 (UNE-EN 15619) o C-s2,d0. Pública concurrencia: butacas tapizadas UNE-EN 1021-1 y -2; textiles suspendidos Clase 1 UNE-EN 13773. Cables y similares: reglamentación específica.

## 6. SI 2 — Propagación exterior

- **Medianerías**: elementos verticales separadores de otro edificio ≥ EI 120.
- **Propagación horizontal por fachada** (entre sectores, desde riesgo especial alto, o hacia escalera/pasillo protegido): puntos no EI 60 separados en proyección horizontal al menos d según el ángulo α entre fachadas (interpolar):

| α | 0º (enfrentadas paralelas) | 45º | 60º | 90º | 135º | 180º |
|---|---|---|---|---|---|---|
| d (m) | 3,00 | 2,75 | 2,50 | 2,00 | 1,25 | 0,50 |

  Entre edificios colindantes: 50 % de d hasta la bisectriz del ángulo.
- **Propagación vertical**: fachada EI 60 en franja de ≥ 1 m de altura (reducible en la dimensión de salientes aptos).
- **Reacción al fuego de sistemas de fachada** (> 10 % de su superficie, según altura total): ≤ 10 m D-s3,d0; ≤ 18 m C-s3,d0; > 18 m B-s3,d0. **Aislamiento en cámaras ventiladas**: ≤ 10 m D-s3,d0; ≤ 28 m B-s3,d0; > 28 m A2-s3,d0. Limitar desarrollo vertical de cámaras en forjados sectorizadores (barreras E 30 válidas). Fachadas ≤ 18 m con arranque accesible al público (rasante o cubierta): ≥ B-s3,d0 hasta ≥ 3,5 m.
- **Cubiertas**: REI 60 en franja de 0,50 m desde el edificio colindante y de 1,00 m sobre el encuentro con todo elemento compartimentador de sector o de local de riesgo especial alto; alternativa: prolongar la medianería/elemento 0,60 m sobre el acabado.
- **Encuentro cubierta–fachada** de sectores/edificios distintos: altura h de zona de fachada no EI 60 sobre zona de cubierta no EI 60 a distancia horizontal d:

| d (m) | ≥2,50 | 2,00 | 1,75 | 1,50 | 1,25 | 1,00 | 0,75 | 0,50 | 0 |
|---|---|---|---|---|---|---|---|---|---|
| h (m) | 0 | 1,00 | 1,50 | 2,00 | 2,50 | 3,00 | 3,50 | 4,00 | 5,00 |

- Materiales > 10 % del acabado exterior de cubierta a < 5 m de la proyección de fachada no EI 60 (incl. cara superior de voladizos > 1 m, lucernarios, claraboyas): **BROOF (t1)**.

## 7. SI 3 — Evacuación de ocupantes

### 7.1 Compatibilidad (SI 3-1)
Establecimientos Comercial o Pública concurrencia (cualquier S) y Docente, Hospitalario, Residencial Público o Administrativo > 1.500 m², integrados en edificio de otro uso principal: salidas de uso habitual y recorridos a espacio exterior seguro independientes de las zonas comunes y compartimentados como el establecimiento; salidas de emergencia pueden dar a elemento común a través de vestíbulo de independencia si está dimensionado para ello. Excepción: Pública concurrencia ≤ 500 m² en centros comerciales puede salir a zonas comunes; > 500 m², al menos las de emergencia independientes.

### 7.2 Ocupación (tabla 2.1, m²/persona sobre superficie útil)
Considerar simultaneidad o alternancia de zonas; usar ocupación mayor si es previsible.

| Uso | Zona | m²/pers |
|---|---|---|
| Cualquiera | Ocupación ocasional/mantenimiento (salas de máquinas, limpieza) | nula |
| Cualquiera | Aseos de planta | 3 |
| Res. Vivienda | Plantas de vivienda | 20 |
| Res. Público | Zonas de alojamiento | 20 |
| Res. Público | Salones de uso múltiple | 1 |
| Res. Público | Vestíbulos generales y zonas de uso público en sótano, baja y entreplanta | 2 |
| Aparcamiento | Vinculado a actividad con horarios (comercial, espectáculos, oficina) | 15 |
| Aparcamiento | Otros casos (incl. transporte de personas/mercancías) | 40 |
| Administrativo | Plantas o zonas de oficinas | 10 |
| Administrativo | Vestíbulos generales y zonas de uso público | 2 |
| Docente | Conjunto de la planta o edificio | 10 |
| Docente | Laboratorios, talleres, gimnasios, salas de dibujo | 5 |
| Docente | Aulas (excepto escuelas infantiles) | 1,5 |
| Docente | Aulas de escuelas infantiles y salas de lectura de bibliotecas | 2 |
| Hospitalario | Salas de espera | 2 |
| Hospitalario | Zonas de hospitalización | 15 |
| Hospitalario | Servicios ambulatorios y de diagnóstico | 10 |
| Hospitalario | Tratamiento a pacientes internados | 20 |
| Comercial | Áreas de venta en sótano, baja y entreplanta | 2 |
| Comercial | Áreas de venta en otras plantas | 3 |
| Comercial (zonas comunes CC) | Mercados y galerías de alimentación | 2 |
| Comercial (zonas comunes CC) | Sótano, baja, entreplanta o con acceso desde el exterior | 3 |
| Comercial (zonas comunes CC) | Otras plantas | 5 |
| Comercial | Ventas sin gran afluencia (muebles, vehículos…) | 5 |
| Pública concurrencia | Espectadores sentados con asientos definidos | 1 pers/asiento |
| Pública concurrencia | Espectadores sentados sin asientos definidos | 0,5 |
| Pública concurrencia | Espectadores de pie | 0,25 |
| Pública concurrencia | Público en discotecas | 0,5 |
| Pública concurrencia | Público de pie en bares, cafeterías | 1 |
| Pública concurrencia | Gimnasios con aparatos / sin aparatos | 5 / 1,5 |
| Pública concurrencia | Piscinas: vasos / estancia en descubiertas / vestuarios | 2 / 4 / 3 |
| Pública concurrencia | Salones de uso múltiple (congresos, hoteles) | 1 |
| Pública concurrencia | Restaurantes de comida rápida | 1,2 |
| Pública concurrencia | Público sentado en bares, cafeterías, restaurantes | 1,5 |
| Pública concurrencia | Salas de espera, lectura, museos, galerías, ferias | 2 |
| Pública concurrencia | Vestíbulos generales y uso público en sótano, baja, entreplanta | 2 |
| Pública concurrencia | Vestíbulos, vestuarios, camerinos anejos a salas | 2 |
| Pública concurrencia | Terminales de transporte | 10 |
| Pública concurrencia | Zonas de servicio de bares, restaurantes | 10 |
| Archivos, almacenes | — | 40 |

Ocupación = Σ S_útil / densidad por zona. El DB-SI no fija el redondeo: este skill redondea al entero superior por zona como **criterio adoptado** (decláralo en "Supuestos"). Aparcamientos robotizados: sin ocupación.

### 7.3 Número de salidas y longitud de recorridos (tabla 3.1)
**Una única salida de planta/recinto** — se admite sólo si se cumplen todas:
- No es planta de hospitalización/tratamiento intensivo ni sala/unidad de hospitalizados > 90 m².
- Ocupación ≤ 100 personas (≤ 500 en el conjunto del edificio para salida de edificio de viviendas; ≤ 50 si hay que salvar > 2 m ascendentes hasta salida de planta; ≤ 50 alumnos en infantil, primaria o secundaria).
- Recorrido hasta salida de planta ≤ 25 m (35 m en Aparcamiento; 50 m si la planta tiene salida directa a espacio exterior seguro y ocupación ≤ 25, o espacio al aire libre de riesgo irrelevante).
- Altura de evacuación descendente ≤ 28 m (Res. Público: máximo segunda planta sobre la de salida, o 28 m si ≤ 20 plazas con detección y alarma) o ≤ 10 m si es ascendente.

**Más de una salida**:
- Recorrido hasta alguna salida de planta ≤ 50 m (35 m con ocupantes que duermen, hospitalización/tratamiento intensivo, infantil o primaria; 75 m al aire libre de riesgo irrelevante).
- Desde el origen hasta un punto con dos recorridos alternativos: ≤ 15 m en hospitalización/tratamiento intensivo; en el resto, ≤ la longitud máxima admitida con salida única.
- Si la altura descendente obliga a > 1 salida, o > 50 personas salvan > 2 m ascendentes: al menos dos salidas de planta a dos escaleras diferentes.
- Planta de salida del edificio con > 1 salida: Res. Vivienda si ocupación total > 500; otros usos si lo exige su propia ocupación o si el edificio necesita > 1 escalera (desc. o asc.).

**+25 %** en todas las longitudes si el sector tiene instalación automática de extinción.

### 7.4 Asignación de ocupantes (SI 3-4.1)
- Con varias salidas (incluidos puntos de paso obligado): repartir suponiendo **inutilizada una**, en la hipótesis más desfavorable.
- Escaleras: no hace falta inutilizar una protegida, especialmente protegida o compartimentada como sector; sí una no protegida no compartimentada cuando deba haber varias.
- En la planta de desembarco, sumar a la salida de planta el flujo de la escalera: 160·A personas (A = ancho del desembarco, m) o el nº real de usuarios si es menor.

### 7.5 Dimensionado (tabla 4.1)
| Elemento | Criterio |
|---|---|
| Puertas y pasos | A ≥ P/200 ≥ 0,80 m. Hoja: 0,60 ≤ ancho ≤ 1,23 m. Puerta de salida de escalera protegida a planta de salida: ≥ 80 % de la anchura de cálculo de la escalera. Hospitalario: A ≥ 1,05 m (incl. habitaciones) |
| Pasillos y rampas | A ≥ P/200 ≥ 1,00 m (0,80 m si ≤ 10 personas usuarios habituales). Hospitalario: ≥ 2,20 m (2,10 m en paso por puertas) |
| Comercial, pasillos de áreas de venta (> 400 m² en la planta) | con carros: 4,00 m entre baterías de > 10 cajas y estanterías, 1,80 m otros; sin carros 1,40 m |
| Comercial, áreas de venta ≤ 400 m² | con carros: 3,00 m entre baterías de > 10 cajas y estanterías, 1,40 m otros; sin carros 1,20 m |
| Pasos entre filas de asientos fijos | salida por un extremo: ≥ 30 cm con 7 asientos + 2,5 cm por asiento adicional, máx. 12 asientos; por ambos extremos: ≥ 30 cm hasta 14 asientos + 1,25 cm por adicional; ≥ 30 asientos: ≥ 50 cm. Cada ≤ 25 filas, paso ≥ 1,20 m |
| Escaleras no protegidas | descendente A ≥ P/160; ascendente A ≥ P/(160 − 10h) |
| Escaleras protegidas | E ≤ 3·S + 160·AS |
| Pasillos protegidos | P ≤ 3·S + 200·A |
| Aire libre | pasos, pasillos, rampas A ≥ P/600; escaleras A ≥ P/480 |

A = anchura (m); AS = anchura de la escalera protegida en su desembarco en planta de salida; h = altura de evacuación ascendente (m); P = personas que pasan por el punto; E = ocupantes asignados a la escalera en la planta más los de las plantas inferiores/superiores hasta la de salida (bloqueo de salidas sólo en una planta, la más desfavorable); S = superficie útil de la escalera protegida en el conjunto de plantas (tramos, rellanos, mesetas) o del pasillo protegido. Anchura mínima de escaleras: DB SUA 1-4.2.2 tabla 4.1 (fuera de este DB; pídela o márcala).

**Tabla 4.2 — Capacidad de escaleras (nº de ocupantes)**

| A (m) | No prot. asc. | No prot. desc. | Prot. 2 pl. | 4 pl. | 6 pl. | 8 pl. | 10 pl. | + cada planta |
|---|---|---|---|---|---|---|---|---|
| 1,00 | 132 | 160 | 224 | 288 | 352 | 416 | 480 | +32 |
| 1,10 | 145 | 176 | 248 | 320 | 392 | 464 | 536 | +36 |
| 1,20 | 158 | 192 | 274 | 356 | 438 | 520 | 602 | +41 |
| 1,30 | 171 | 208 | 302 | 396 | 490 | 584 | 678 | +47 |
| 1,40 | 184 | 224 | 328 | 432 | 536 | 640 | 744 | +52 |
| 1,50 | 198 | 240 | 356 | 472 | 588 | 704 | 820 | +58 |
| 1,60 | 211 | 256 | 384 | 512 | 640 | 768 | 896 | +64 |
| 1,70 | 224 | 272 | 414 | 556 | 698 | 840 | 982 | +71 |
| 1,80 | 237 | 288 | 442 | 596 | 750 | 904 | 1058 | +77 |
| 1,90 | 250 | 304 | 472 | 640 | 808 | 976 | 1144 | +84 |
| 2,00 | 264 | 320 | 504 | 688 | 872 | 1056 | 1240 | +92 |
| 2,10 | 277 | 336 | 534 | 732 | 930 | 1128 | 1326 | +99 |
| 2,20 | 290 | 352 | 566 | 780 | 994 | 1208 | 1422 | +107 |
| 2,30 | 303 | 368 | 598 | 828 | 1058 | 1288 | 1518 | +115 |
| 2,40 | 316 | 384 | 630 | 876 | 1122 | 1368 | 1614 | +123 |

Protegida: válida para doble tramo de anchura constante con rellanos estrictos; otras configuraciones → fórmula E ≤ 3S + 160AS calculando S del modelo. No protegidas ascendentes > 2,80 m: máx. 100 personas.

### 7.6 Protección de escaleras (tabla 5.1) — h = altura de evacuación de la escalera
**Descendente**

| Uso | No protegida | Protegida | Especialmente protegida |
|---|---|---|---|
| Res. Vivienda | h ≤ 14 m | h ≤ 28 m | en todo caso |
| Administrativo, Docente | h ≤ 14 m | h ≤ 28 m | en todo caso |
| Comercial, Pública concurrencia | h ≤ 10 m | h ≤ 20 m | en todo caso |
| Res. Público | baja más una | h ≤ 28 m (< 20 plazas: detección y alarma como alternativa) | en todo caso |
| Hospitalario, hospitalización/tratamiento intensivo | no se admite | h ≤ 14 m | en todo caso |
| Hospitalario, otras zonas | h ≤ 10 m | h ≤ 20 m | en todo caso |
| Aparcamiento | no se admite | no se admite | en todo caso |

**Ascendente**: Aparcamiento → sólo especialmente protegida. Otro uso: h ≤ 2,80 m → cualquiera; 2,80 < h ≤ 6,00 m → no protegida sólo si P ≤ 100, protegida en todo caso; h > 6,00 m → no protegida no se admite.
La escalera cumple en cada planta lo más restrictivo de los sectores que comunica. Escaleras entre sectores con h dentro del límite de no protegida: basta compartimentarlas para mantener la sectorización (o incorporarlas a un sector).

### 7.7 Puertas en recorridos (SI 3-6)
- Salidas de planta/edificio y puertas para > 50 personas: **abatibles de eje vertical**; cierre inactivo con actividad o apertura fácil sin llave y con un solo mecanismo (UNE-EN 179 si usuarios familiarizados; UNE-EN 1125 barra antipánico si no y abre en sentido de evacuación). No aplica a puertas automáticas.
- **Abren en sentido de evacuación** si: > 200 personas (Res. Vivienda) o > 100 personas (resto), o > 50 ocupantes del recinto donde está (con asignación de 4.1).
- Giratorias: puerta abatible manual contigua, salvo automáticas abatibles con ≤ 220 N.
- Automáticas: ante fallo/emergencia abrir y mantener abiertas o abatir en sentido de evacuación (correderas ≤ 220 N, no en itinerario accesible; abatibles ≤ 150 N, en itinerario accesible ≤ 25 N o ≤ 65 N si resistente al fuego), fuerza a 1000 ± 10 mm; mantenimiento UNE 85121:2018.

### 7.8 Señalización (SI 3-7)
UNE 23034. "SALIDA" en salidas de recinto, planta o edificio (no en Res. Vivienda ni recintos ≤ 50 m² visibles y de usuarios familiarizados); "Salida de emergencia" en las exclusivas de emergencia; señales de dirección visibles desde todo origen sin visión de la salida y frente a salidas de recintos > 100 personas a pasillo lateral; en bifurcaciones y escaleras que continúan bajo la planta de salida; "Sin salida" junto a puertas que induzcan a error (no sobre la hoja); coherentes con la asignación; itinerarios accesibles con SIA y "ZONA DE REFUGIO"; zonas de refugio con pavimento de color distinto. Visibles con fallo de alumbrado (fotoluminiscentes UNE 23035-1/2/4, mantenimiento 23035-3).

### 7.9 Control de humo (SI 3-8)
Obligatorio en: Aparcamiento no abierto; Comercial o Pública concurrencia con ocupación > 1000; atrios con > 500 personas en el sector o usados por > 500. Normas UNE 23584, 23585, UNE-EN 12101-6. Aparcamientos con ventilación DB HS-3 mecánica: extracción 150 l/plaza·s, aportación máx. 120 l/plaza·s, activación por detección; plantas > 4 m: compuertas E300 60 en aberturas bajas; ventiladores F300 60; conductos E300 60 (EI 60 si atraviesan sectores).

### 7.10 Personas con discapacidad (SI 3-9)
Aplica a: Res. Vivienda h > 28 m; Res. Público, Administrativo, Docente h > 14 m; Comercial, Pública concurrencia h > 10 m; plantas de Aparcamiento > 1.500 m². Toda planta (no ocupación nula) sin salida de edificio accesible: paso a sector alternativo por salida de planta accesible o **zona de refugio** con 1 plaza silla de ruedas por cada 100 ocupantes o fracción y (salvo Res. Vivienda) 1 plaza de otra movilidad reducida por cada 33 o fracción. Itinerario accesible desde todo origen en zona accesible hasta ellas; planta de salida con itinerario accesible hasta salida de edificio accesible.

## 8. SI 4 — Instalaciones de protección contra incendios (tabla 1.1)
Diseño/mantenimiento según RIPCI (RD 513/2017). Locales de riesgo especial y zonas subsidiarias que sean sector propio: dotación de su uso, nunca inferior a la del uso principal.

**En general**
- Extintores 21A-113B: a ≤ 15 m de recorrido en cada planta desde todo origen; en zonas de riesgo especial uno exterior junto a la puerta y los interiores necesarios para recorrido ≤ 15 m (bajo/medio) o ≤ 10 m (alto).
- BIE: riesgo especial alto por combustibles sólidos (45 mm; 25 mm en Res. Vivienda).
- Ascensor de emergencia: plantas con h_evac > 28 m.
- Hidrantes: h desc > 28 m o asc > 6 m, o establecimientos con densidad > 1 pers/5 m² y 2.000–10.000 m²; 1 hasta 10.000 m² + 1 por cada 10.000 m² o fracción (cuentan los públicos a < 100 m de la fachada accesible).
- Extinción automática: edificios con h_evac > 80 m; cocinas > 20 kW (Hospitalario, Res. Público) o > 50 kW (resto); CT con dieléctrico < 300 ºC y > 1.000 kVA por aparato o > 4.000 kVA total (630 / 2.520 kVA si en Pública concurrencia con acceso interior).

| Uso | Exigencias específicas |
|---|---|
| Res. Vivienda | Columna seca h > 24 m · Detección y alarma h > 50 m · Hidrante 1 entre 5.000–10.000 m² (+1/10.000 m²) |
| Administrativo | BIE S > 2.000 m² · Columna seca h > 24 m · Alarma S > 1.000 m² · Detección: S > 2.000 m² en zonas de riesgo alto, S > 5.000 m² en todo el edificio · Hidrante 5.000–10.000 m² |
| Res. Público | BIE S > 1.000 m² o > 50 alojados · Columna seca h > 24 m · Detección y alarma S > 500 m² · Extinción automática h > 28 m o S > 5.000 m² · Hidrante 2.000–10.000 m² |
| Hospitalario | Extintor móvil 25 kg polvo/CO₂ por 2.500 m² en riesgo alto > 500 m² · Columna seca h > 15 m · BIE en todo caso · Detección y alarma en todo caso (detectores, pulsadores, alarma local/general, instrucciones verbales; > 100 camas: línea directa con bomberos) · Ascensor de emergencia en hospitalización/tratamiento intensivo con h > 15 m · Hidrante 2.000–10.000 m² |
| Docente | BIE S > 2.000 m² · Columna seca h > 24 m · Alarma S > 1.000 m² · Detección: S > 2.000 m² en riesgo alto, > 5.000 m² todo · Hidrante 5.000–10.000 m² |
| Comercial | Extintores móviles 50 kg polvo: 1 por cada 1.000 m² sobre 1.000 m² en agrupaciones de riesgo especial medio/alto · BIE S > 500 m² · Columna seca h > 24 m · Alarma S > 1.000 m² · Detección S > 2.000 m² · Extinción automática si área pública de ventas > 1.500 m² y carga de fuego > 500 MJ/m² (área y locales de riesgo medio/alto) · Hidrante 1.000–10.000 m² |
| Pública concurrencia | BIE S > 500 m² · Columna seca h > 24 m · Alarma con megafonía si ocupación > 500 · Detección S > 1.000 m² · Hidrantes: cines, teatros, auditorios, discotecas 500–10.000 m²; recintos deportivos 5.000–10.000 m² |
| Aparcamiento | BIE S > 500 m² (no robotizados) · Columna seca > 3 plantas bajo rasante o > 4 sobre rasante · Detección convencionales > 500 m²; robotizados pulsadores · Hidrante 1.000–10.000 m² · Extinción automática en robotizados |

BIE de 25 mm salvo indicación. Alarma con señales visuales además de acústicas. Señalización de instalaciones manuales: RIPCI.

## 9. SI 5 — Intervención de los bomberos
- **Viales de aproximación**: anchura libre ≥ 3,5 m; gálibo ≥ 4,5 m; capacidad portante 20 kN/m²; en curvas, corona con radios 5,30 m y 12,50 m y anchura libre 7,20 m.
- **Espacio de maniobra** (h_evac desc > 9 m), a lo largo de fachadas con accesos: anchura ≥ 5 m; altura libre la del edificio; separación máx. vehículo–fachada 23 m (h ≤ 15 m), 18 m (15–20 m), 10 m (> 20 m); distancia máx. a accesos 30 m; pendiente ≤ 10 %; punzonamiento 100 kN sobre 20 cm Ø (también tapas > 0,15 × 0,15 m, UNE-EN 124); libre de obstáculos y cables/ramas.
- Columna seca: acceso de bombeo a < 18 m de cada conexión, visible desde el camión. Viales sin salida > 20 m: espacio de maniobra.
- **Interfaz urbano-forestal**: franja de 25 m libre de vegetación + camino perimetral de 5 m; preferentemente dos accesos; si uno, fondo de saco circular de 12,50 m de radio.
- **Huecos de fachada** (en las fachadas del espacio de maniobra): alféizar ≤ 1,20 m sobre la planta; hueco ≥ 0,80 m (horizontal) × 1,20 m (vertical); ejes de huecos consecutivos ≤ 25 m; sin elementos que impidan el acceso salvo seguridad en plantas con h ≤ 9 m.
- Aparcamientos robotizados: vía compartimentada EI 120 con puertas EI2 60-C5 a cada nivel y extracción mecánica de 3 renovaciones/hora.

## 10. SI 6 — Resistencia al fuego de la estructura

**Tabla 3.1 — Elementos estructurales principales**

| Uso del sector | Sótano | h ≤ 15 m | h ≤ 28 m | h > 28 m |
|---|---|---|---|---|
| Vivienda unifamiliar | R 30 | R 30 | – | – |
| Res. Vivienda, Res. Público, Docente, Administrativo | R 120 | R 60 | R 90 | R 120 |
| Comercial, Pública concurrencia, Hospitalario | R 120 (R 180 si h > 28 m) | R 90 | R 120 | R 180 |
| Aparcamiento (edificio exclusivo o situado sobre otro uso) | R 90 (cualquier planta) | | | |
| Aparcamiento (situado bajo un uso distinto) | R 120; R 180 si robotizado (cualquier planta) | | | |

Suelo entre sectores: según uso del sector inferior. Unifamiliares agrupadas/adosadas: estructura común como Res. Vivienda.
**Tabla 3.2 — Zonas de riesgo especial**: bajo R 90; medio R 120; alto R 180 (no menor que la de la planta; R 30 bajo cubierta no evacuable sin riesgo para otras plantas).
- Cubiertas ligeras (carga permanente del cerramiento ≤ 1 kN/m²) no evacuables, a ≤ 28 m de la rasante: R 30 si su fallo no afecta a otros edificios, plantas inferiores ni sectorización.
- Estructura de escaleras/pasillos protegidos contenida en su recinto: ≥ R 30; especialmente protegidas: sin exigencia.
- Elementos secundarios (entreplantas pequeñas, escaleras ligeras…) cuyo colapso no afecte a ocupantes, estabilidad, evacuación ni sectorización: sin exigencia; pero todo suelo que deba tener R de tabla 3.1 debe ser accesible por una escalera con esa misma R o protegida.
- Estructuras de carpas: R 30, salvo textil T2/C-s2,d0 con perforación ≥ 20 cm² tras UNE-EN 14115.
- Acciones: Efi,d = ηfi·Ed, ηfi = (GK + ψ1,1·QK,1)/(γG·GK + γQ,1·QK,1); γM,fi = 1; μfi = Efi,d / Rfi,d,0.

**Comprobación geométrica desde el modelo** (cuando el usuario aporte material y recubrimientos):
- *Hormigón, tabla C.2 (bmín / am en mm)* — soportes: R30 150/15 · R60 200/20 · R90 250/30 · R120 250/40 · R180 350/45 · R240 400/50. Muro de carga expuesto por una cara (puede considerarse REI): R30 100/15, R60 120/15, R90 140/20, R120 160/25, R180 200/40, R240 250/50. Muro ambas caras: R30 120/15, R60 140/15, R90 160/25, R120 180/35, R180 250/45, R240 300/50. (Soportes in situ ≥ 250 mm según EHE.)
- *Vigas tres caras, tabla C.3 (bmín/am, opciones 1–4; b0,mín alma)*: R30 80/20, 120/15, 200/10 (alma 80) · R60 100/30, 150/25, 200/20 (100) · R90 150/40, 200/35, 250/30, 400/25 (100) · R120 200/50, 250/45, 300/40, 500/35 (120) · R180 300/75, 350/65, 400/60, 600/50 (140) · R240 400/75, 500/70, 700/60 (160). Expuestas en todas sus caras: además área ≥ 2·bmín².
- *Losas macizas, tabla C.4 (hmín; am una dirección / dos direcciones ly/lx ≤ 1,5 / 1,5 < ly/lx ≤ 2)*: REI30 60; 10/10/10 · REI60 80; 20/10/20 · REI90 100; 25/15/25 · REI120 120; 35/20/30 · REI180 150; 50/30/40 · REI240 175; 60/50/50.
- *Forjados bidireccionales, tabla C.5 (bmín/am opciones 1–3; hmín)*: REI30 80/20, 120/15, 200/10; 60 · REI60 100/30, 150/25, 200/20; 80 · REI90 120/40, 200/30, 250/25; 100 · REI120 160/50, 250/40, 300/35; 120 · REI180 200/70, 300/60, 400/55; 150 · REI240 250/90, 350/75, 500/70; 175.
- Árido calizo en vigas, losas y forjados: −10 % en dimensiones y am. Yeso: espesor equivalente de hormigón ×1,8. Bovedillas cerámicas: ×2 su espesor. Recubrimiento > 50 mm en tracción: armadura de piel (malla < 150 mm).
- *Acero (Anejo D)*: requiere Am/V, μfi y d/λp (tabla D.1) o cálculo incremental; clase 4: θ ≤ 350 ºC. Marca `NO VERIFICABLE` salvo que el usuario aporte protección certificada (marcado CE).
- *Madera (Anejo E)*: def = βn·t + k0·7 mm (k0 = 1 si t ≥ 20 min; t/20 si menor). βn: coníferas/haya laminada ρk ≥ 290 → 0,70 mm/min; maciza ρk ≥ 290 → 0,80; frondosas ρk = 290 → 0,70, ρk ≥ 450 → 0,55 (interpolar); LVL ρk ≥ 480 → 0,70. Resistencias y rigideces = valores característicos × kfi (maciza 1,25; laminada encolada 1,15; tableros 1,15; LVL 1,10; uniones con piezas laterales de madera/tableros 1,15; uniones con placas de acero externas 1,05) y kmod = 1. Protección: carbonización ×2 tras el fallo del revestimiento hasta min(25 mm, profundidad sin protección). Con la sección del modelo puedes dar la sección eficaz; la capacidad portante requiere cálculo DB SE-M.
- *Isoterma 500 (C.3)*: sólo aplicable si el lado menor de vigas/soportes supera R60 90, R90 120, R120 160, R180 200, R240 280 mm.
- *Fábricas (Anejo F)*, una hoja con revestimiento ≥ 1,5 cm (multihoja: suma de hojas):
  - Ladrillo hueco 40≤e<80 / 80≤e<110 / e≥110 mm: enfoscado cara expuesta – / EI-60 / EI-90; enfoscado dos caras EI-30 / EI-90 / EI-120; guarnecido cara expuesta EI-60 / EI-120 / EI-180; guarnecido dos caras EI-90 / EI-180 / EI-240.
  - Ladrillo macizo o perforado 110≤e<200 / e≥200: sin revestir REI-120 / REI-240; enfoscado cara expuesta EI-180 / REI-240; enfoscado dos caras REI-180 / REI-240; guarnecido cara expuesta EI-240 / REI-240; guarnecido dos caras EI-240 / REI-240.
  - Bloque de arcilla aligerada 140≤e<240 / e≥240: enfoscado cara expuesta EI-180 / EI-240; dos caras REI-180 / REI-240; guarnecido cara expuesta EI-240 / EI-240; dos caras EI-240, RE-240, REI-180 / REI-240.
  - Bloque de hormigón (tabla F.2), cámara simple: silíceo sin revestir 100 EI-15, 150 REI-60, 200 REI-120; calizo sin revestir 100 EI-60, 150 REI-90, 200 REI-180; volcánico sin revestir 120 EI-120, 200 REI-180; volcánico guarnecido dos caras 90 EI-180; volcánico guarnecido cara expuesta (enfoscado exterior) 120 EI-180, 200 REI-240. Cámara doble, arcilla expandida: sin revestir 150 EI-180; guarnecido dos caras 150 RE-240 / REI-80.

**Tiempo equivalente (Anejo B)** — alternativa para estructura y compartimentación (no para locales de instalaciones en tabla 2.2):
- te,d = kb · wf · kc · qf,d (min); kb = 0,07; kc = 1,0 hormigón armado y acero protegido, 13,7·O acero sin proteger.
- wf = (6/H)^0,3 · [0,62 + 90(0,4 − αv)^4 / (1 + bv·αh)] ≥ 0,5; αv = Av/Af (0,025 ≤ αv ≤ 0,25); αh = Ah/Af; bv = 12,5(1 + 10αv − αv²) ≥ 10. Sectores < 100 m² sin aberturas en techo: wf = O^−½ · Af/At, O = Av·√h / At (0,02 ≤ O ≤ 0,20).
- wf simplificado (una planta, huecos sólo en fachada; filas altura 2,5/3,0/3,5/4,0 m; columnas Av/Af 0,05/0,10/0,15/0,20/0,25): 2,5 m → 2,6 1,8 1,3 1,0 0,9 · 3,0 m → 2,4 1,7 1,2 0,9 0,8 · 3,5 m → 2,3 1,6 1,1 0,9 0,8 · 4,0 m → 2,2 1,5 1,1 0,9 0,8.
- qf,d = qf,k · m · δq1 · δq2 · δn · δc; m = 0,8 celulósicos (1 si se desconoce).
  - δq1 (Af m²): < 20 → 1,00; 25 → 1,10; 250 → 1,50; 2.500 → 1,90; 5.000 → 2,00; > 10.000 → 2,13 (interpolar).
  - δq2: Vivienda, Administrativo, Residencial, Docente 1,00; Comercial, Aparcamiento, Hospitalario, Pública concurrencia 1,25; riesgo especial bajo 1,25, medio 1,40, alto 1,60.
  - δn = δn1·δn2·δn3: detección automática 0,87; alarma automática a bomberos 0,87; extinción automática 0,61.
  - δc: h desc > 28 m o asc > 1 planta → 2,0; desc 15–28 m o asc ≤ 2,8 m, aparcamientos bajo otros usos → 1,5; desc < 15 m o aparcamiento exclusivo → 1,0; ×1,5 en hospitales y similares.
  - qf,k variable (MJ/m², tabla B.6): Comercial 730; Res. Vivienda 650; Hospitalario/Res. Público 280; Administrativo 520; Docente 350; Pública concurrencia (teatros, cines) 365; Aparcamiento 280. Más la carga permanente de revestimientos (dato del usuario).
- Curva normalizada: θg = 20 + 345·log10(8t + 1) ºC (≈ 15'→740, 30'→840, 60'→950, 90'→1000, 120'→1050, 180'→1100, 240'→1150 ºC).

## 11. Reformas y cambios de uso (Introducción III)
- Cambio de uso parcial: aplicar a esa parte y a los medios de evacuación que la sirven hasta el espacio exterior seguro (excepción: transformar en vivienda zonas de edificios de vivienda existentes no obliga a los elementos comunes).
- Reforma manteniendo uso: aplicar a los elementos modificados cuando suponga mayor adecuación. Si altera ocupación o su distribución, aplicar también a los elementos de evacuación; si afecta a soporte/paso de instalaciones PCI, adecuarlas.
- La reforma no puede empeorar las condiciones preexistentes. Edificios protegidos: soluciones alternativas de máxima adecuación, documentando limitaciones de uso.
- Zonas con privación de libertad o limitaciones psíquicas: condiciones alternativas justificadas.

## 12. Formato del informe

```
VERIFICACIÓN CTE DB-SI (texto consolidado 4-mar-2025) — <documento FreeCAD>
Fecha · Alcance: <plantas/zonas analizadas> · Tipo de obra: <…>

1. DATOS DE PARTIDA
| Parámetro | Valor | Origen (MODELO/USUARIO/SUPUESTO) |
  uso principal, usos subsidiarios, altura de evacuación desc./asc., superficie construida
  por sector, ocupación total, extinción automática (sí/no), …

2. RESUMEN
  CUMPLE n · NO CUMPLE n · NO VERIFICABLE n · NO APLICA n
  Incumplimientos principales (lista corta, con referencia)

3. COMPROBACIONES
| Ref. | Requisito | Exigido | Proyecto | Resultado | Observaciones |
| SI 1-1 T1.1 | Sup. máx. sector S1 (Administrativo) | ≤ 2.500 m² | 1.830 m² | CUMPLE | |
| SI 3-4 T4.1 | Puerta P-03, P = 230 | A ≥ 1,15 m | 0,90 m | NO CUMPLE | ampliar o redistribuir |
| SI 3-3 T3.1 | Recorrido máx. planta 2 (2 salidas) | ≤ 50 m | 41–58 m (estimado) | NO VERIFICABLE | trazar recorrido |
  (agrupar por SI 1 … SI 6)

4. DATOS QUE FALTAN PARA COMPLETAR LA VERIFICACIÓN
5. SUPUESTOS ADOPTADOS
6. AVISO: verificación orientativa basada en el texto consolidado sin valor jurídico;
   no sustituye la justificación del técnico competente ni otras normas (DB SUA, RIPCI, RSCIEI,
   normativa autonómica/municipal).
```

Reglas del informe:
- Muestra los cálculos intermedios clave (ocupación por recinto, reparto entre salidas con una bloqueada, P/200, etc.).
- Si una exigencia depende de un dato no disponible, indica qué dato y cómo afecta (p. ej. "con extinción automática el límite pasa a 62,5 m").
- Propón medidas correctoras concretas para cada NO CUMPLE.
- Si el usuario lo pide, ofrece marcar en FreeCAD los elementos que no cumplen (cambiar color/agrupar en "NO_CUMPLE_DBSI") — sólo con su permiso, porque modifica el documento.

## 13. Atajos de cálculo frecuentes
- Puerta: A_req = max(0,80; P/200) m (Hospitalario 1,05). Pasillo: max(1,00; P/200).
- Escalera no protegida desc.: P_max = 160·A; asc.: (160 − 10h)·A.
- Escalera protegida: E_max = 3·S + 160·AS.
- Espacio exterior seguro: S ≥ 0,5·P m² dentro de r = 0,1·P m (P > 50).
- Zona de refugio: plazas SR = ceil(occ/100), otras = ceil(occ/33).
- Con extinción automática: superficies de sector ×2, recorridos ×1,25 (también zonas de riesgo especial).
