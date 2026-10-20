"""
Extrae del documento activo de FreeCAD los datos para verificar el CTE DB-SI
y evalúa la calidad del modelo. Sólo lectura: no modifica el documento.

Cómo usarlo:
  - Desde un MCP de FreeCAD: pasar el contenido de este archivo a la herramienta
    que ejecuta código Python (p. ej. `execute_code`).
  - A mano: FreeCAD > Ver > Paneles > Consola de Python y pegarlo, o
    Macro > Macros... > ejecutar este archivo.

Detecta automáticamente tres situaciones:
  1. IFC abierto en modo NATIVO (FreeCAD 1.x, banco BIM): lee el IFC en memoria con
     IfcOpenShell (incluido en FreeCAD), aunque los elementos no estén desplegados
     en el árbol.
  2. Modelo BIM "clásico" (objetos Arch/BIM, IFC importado o modelado en FreeCAD).
  3. Plano 2D (Draft, Sketch, DXF importado).
Si no reconoce nada, lo dice y muestra un DIAGNÓSTICO de los tipos de objeto
encontrados en lugar de suponer que es 2D.

Imprime un bloque JSON entre ===DBSI_JSON_INICIO=== y ===DBSI_JSON_FIN===.
Todo en metros y m².
"""
import json
from collections import Counter

import FreeCAD as App

doc = App.ActiveDocument
if doc is None:
    raise SystemExit("No hay documento activo en FreeCAD")

# --------------------------------------------------------------------------
# Utilidades comunes
# --------------------------------------------------------------------------
# Nombres "clásicos" de IfcType/IfcRole en FreeCAD -> clase IFC
CLASICO_A_IFC = {
    "Building Storey": "IfcBuildingStorey", "Building": "IfcBuilding", "Site": "IfcSite",
    "Space": "IfcSpace", "Wall": "IfcWall", "Door": "IfcDoor", "Window": "IfcWindow",
    "Stair": "IfcStair", "Stair Flight": "IfcStairFlight", "Ramp": "IfcRamp",
    "Slab": "IfcSlab", "Column": "IfcColumn", "Beam": "IfcBeam", "Roof": "IfcRoof",
    "Fire Suppression Terminal": "IfcFireSuppressionTerminal", "Alarm": "IfcAlarm",
    "Sensor": "IfcSensor", "Covering": "IfcCovering", "Furniture": "IfcFurniture",
}


def clase_ifc(o):
    """Clase IFC normalizada de un objeto FreeCAD (modo nativo o clásico)."""
    c = str(getattr(o, "Class", "") or "")
    if c.startswith("Ifc"):
        return c
    t = str(getattr(o, "IfcType", "") or getattr(o, "IfcRole", "") or "")
    if t in CLASICO_A_IFC:
        return CLASICO_A_IFC[t]
    if t:
        return "Ifc" + t.replace(" ", "")
    if o.TypeId.endswith("Floor"):
        return "IfcBuildingStorey"
    if o.TypeId.endswith("Stairs"):
        return "IfcStair"
    return ""


def a_metros(v):
    """Quantity de FreeCAD (mm) o número -> metros."""
    try:
        if hasattr(v, "Value") and hasattr(v, "Unit"):
            return round(float(v.Value) / 1000.0, 3)
        return round(float(v) / 1000.0, 3)
    except Exception:
        return None


def bbox_fc(o):
    try:
        b = o.Shape.BoundBox
        if not b.isValid():
            return None
        return [round(x / 1000.0, 3) for x in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)]
    except Exception:
        return None


def diagnostico():
    tids = Counter(o.TypeId for o in doc.Objects)
    clases = Counter(clase_ifc(o) or "(sin clase)" for o in doc.Objects)
    return {
        "objetos_totales": len(doc.Objects),
        "TypeId_mas_frecuentes": tids.most_common(12),
        "clases_ifc_detectadas": clases.most_common(15),
        "propiedades_documento": [p for p in getattr(doc, "PropertiesList", []) if "Ifc" in p],
    }


# --------------------------------------------------------------------------
# 1) Modo IFC nativo: obtener el archivo IFC en memoria
# --------------------------------------------------------------------------
def obtener_ifc_nativo():
    try:
        import ifcopenshell  # incluido en FreeCAD 1.x
    except ImportError:
        return None, "IfcOpenShell no disponible en este FreeCAD"
    # a) API del banco BIM nativo
    try:
        from nativeifc import ifc_tools
        candidatos = [doc] + [o for o in doc.Objects
                              if hasattr(o, "StepId") or hasattr(o, "IfcFilePath")
                              or str(getattr(o, "Class", "")).startswith("Ifc")]
        for c in candidatos:
            try:
                f = ifc_tools.get_ifcfile(c)
                if f:
                    return f, "IFC nativo (archivo en memoria vía nativeifc)"
            except Exception:
                continue
    except ImportError:
        pass
    # b) ruta del archivo guardada como propiedad
    rutas = [getattr(doc, "IfcFilePath", None)] + [getattr(o, "IfcFilePath", None) for o in doc.Objects]
    for r in rutas:
        if r:
            try:
                return ifcopenshell.open(r), f"IFC nativo (leído del disco: {r}; cambios sin guardar no incluidos)"
            except Exception:
                continue
    return None, None


def extraer_de_ifc(f):
    import ifcopenshell.util.element as ue
    import ifcopenshell.util.unit as uu
    try:
        import ifcopenshell.geom as geom
        s = geom.settings()
        s.set("use-world-coords", True)
    except Exception:
        geom = None

    escala = uu.calculate_unit_scale(f)

    def bbox(e):
        if geom is None:
            return None
        try:
            forma = geom.create_shape(s, e)  # conservar la referencia: si se encadena, la
            v = list(forma.geometry.verts)    # geometría puede liberarse y devolver vértices vacíos
            if not v:
                return None
            xs, ys, zs = v[0::3], v[1::3], v[2::3]
            return [round(float(x), 3) for x in (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))]
        except Exception:
            return None

    def psets(e):
        try:
            ps = ue.get_psets(e)
            for d in ps.values():
                d.pop("id", None)
            return ps
        except Exception:
            return {}

    def prop(ps, nombre):
        for d in ps.values():
            if d.get(nombre) not in (None, ""):
                return d[nombre]
        return None

    def planta(e):
        try:
            c = ue.get_container(e)
            return c.Name if c else None
        except Exception:
            return None

    def m(v):
        return round(float(v) * escala, 3) if v is not None else None

    datos = {"plantas": [], "espacios": [], "puertas": [], "muros": [], "escaleras": [],
             "ventanas": [], "pci": []}
    bld = f.by_type("IfcBuilding")
    datos["edificio"] = {"nombre": bld[0].Name if bld else None, "psets": psets(bld[0]) if bld else {}}
    try:
        datos["descripcion_cabecera"] = list(f.header.file_description.description)
    except Exception:
        datos["descripcion_cabecera"] = []
    for st in f.by_type("IfcBuildingStorey"):
        datos["plantas"].append({"nombre": st.Name, "cota_m": m(st.Elevation)})
    for sp in f.by_type("IfcSpace"):
        ps = psets(sp)
        area = prop(ps, "NetFloorArea") or prop(ps, "GrossFloorArea")
        bb = bbox(sp)
        if area is None and bb:
            area = (bb[3] - bb[0]) * (bb[4] - bb[1])
        datos["espacios"].append({"nombre": sp.Name, "nombre_largo": sp.LongName, "planta": planta(sp),
                                  "area_m2": round(float(area), 2) if area is not None else None,
                                  "uso": prop(ps, "OccupancyType") or prop(ps, "Category"), "bbox": bb})
    for d in f.by_type("IfcDoor"):
        ps = psets(d)
        datos["puertas"].append({"nombre": d.Name, "planta": planta(d), "ancho_total_m": m(d.OverallWidth),
                                 "alto_m": m(d.OverallHeight),
                                 "tipo_operacion": str(getattr(d, "OperationType", "") or ""),
                                 "salida_emergencia": prop(ps, "FireExit"),
                                 "resistencia_fuego": prop(ps, "FireRating"), "bbox": bbox(d)})
    for w in f.by_type("IfcWall"):
        ps = psets(w)
        bb = bbox(w)
        datos["muros"].append({
            "nombre": w.Name, "planta": planta(w),
            "espesor_m": round(min(bb[3] - bb[0], bb[4] - bb[1]), 3) if bb else None,
            "exterior": prop(ps, "IsExternal"), "portante": prop(ps, "LoadBearing"),
            "resistencia_fuego": prop(ps, "FireRating"),
            "material": [x.Name for x in (ue.get_materials(w) or []) if getattr(x, "Name", None)],
            "bbox": bb})
    for e in f.by_type("IfcStair"):
        datos["escaleras"].append({"nombre": e.Name, "planta": planta(e), "bbox": bbox(e)})
    for e in f.by_type("IfcWindow"):
        datos["ventanas"].append({"nombre": e.Name, "ancho_m": m(e.OverallWidth), "alto_m": m(e.OverallHeight)})
    for t in ("IfcFireSuppressionTerminal", "IfcAlarm", "IfcSensor"):
        for e in f.by_type(t):
            datos["pci"].append({"nombre": e.Name, "clase": t, "bbox": bbox(e)})
    datos["estructura"] = {t: len(f.by_type(t)) for t in ("IfcColumn", "IfcBeam", "IfcSlab", "IfcRoof")}
    return datos


# --------------------------------------------------------------------------
# 2) Modo BIM clásico (objetos Arch/BIM de FreeCAD)
# --------------------------------------------------------------------------
def planta_fc(o):
    for p in getattr(o, "InListRecursive", []):
        if clase_ifc(p) == "IfcBuildingStorey":
            return p.Label
    return None


def props_ifc_fc(o):
    try:
        return dict(getattr(o, "IfcProperties", {}) or {})
    except Exception:
        return {}


def extraer_de_freecad():
    datos = {"plantas": [], "espacios": [], "puertas": [], "muros": [], "escaleras": [],
             "ventanas": [], "pci": [], "edificio": {"nombre": None, "psets": {}},
             "descripcion_cabecera": [], "estructura": Counter()}
    for o in doc.Objects:
        c = clase_ifc(o)
        if c == "IfcBuildingStorey":
            datos["plantas"].append({"nombre": o.Label, "cota_m": a_metros(o.Placement.Base.z)})
        elif c == "IfcBuilding":
            datos["edificio"]["nombre"] = o.Label
            # Uso declarado: propiedades IFC, propiedades propias o descripción del edificio
            pr = props_ifc_fc(o)
            uso_b = next((v for k, v in pr.items() if "occupancytype" in k.lower() or k.lower() in ("uso", "use")), None)
            for nombre in ("OccupancyType", "Uso", "Use"):
                uso_b = uso_b or (str(getattr(o, nombre, "") or "") or None)
            uso_b = uso_b or (str(getattr(o, "Description", "") or "") or None)
            datos["edificio"]["psets"] = {"FreeCAD": {"OccupancyType": uso_b}} if uso_b else {}
        elif c == "IfcSpace":
            datos["espacios"].append({
                "nombre": o.Label, "planta": planta_fc(o),
                "area_m2": round(float(getattr(o, "Area", 0)) / 1e6, 2) if hasattr(o, "Area") else None,
                "uso": str(getattr(o, "SpaceType", "") or getattr(o, "Description", "")) or None,
                "bbox": bbox_fc(o)})
        elif c == "IfcDoor":
            datos["puertas"].append({
                "nombre": o.Label, "planta": planta_fc(o), "ancho_total_m": a_metros(getattr(o, "Width", None)),
                "alto_m": a_metros(getattr(o, "Height", None)), "props_ifc": props_ifc_fc(o), "bbox": bbox_fc(o)})
        elif c == "IfcWindow":
            datos["ventanas"].append({"nombre": o.Label, "ancho_m": a_metros(getattr(o, "Width", None)),
                                      "alto_m": a_metros(getattr(o, "Height", None))})
        elif c == "IfcWall":
            mat = getattr(o, "Material", None)
            pr = props_ifc_fc(o)
            datos["muros"].append({
                "nombre": o.Label, "planta": planta_fc(o), "espesor_m": a_metros(getattr(o, "Width", None)),
                "altura_m": a_metros(getattr(o, "Height", None)),
                "resistencia_fuego": next((v for k, v in pr.items() if "firerating" in k.lower()), None),
                "material": [getattr(mat, "Label", None)] if mat else [], "bbox": bbox_fc(o)})
        elif c in ("IfcStair", "IfcStairFlight"):
            datos["escaleras"].append({"nombre": o.Label, "ancho_m": a_metros(getattr(o, "Width", None)),
                                       "altura_m": a_metros(getattr(o, "Height", None)),
                                       "peldanos": getattr(o, "NumberOfSteps", None), "bbox": bbox_fc(o)})
        elif c in ("IfcFireSuppressionTerminal", "IfcAlarm", "IfcSensor") or \
                (c and "extint" in o.Label.lower()):  # sólo objetos BIM; no símbolos/textos 2D
            datos["pci"].append({"nombre": o.Label, "clase": c, "bbox": bbox_fc(o)})
        elif c in ("IfcColumn", "IfcBeam", "IfcSlab", "IfcRoof"):
            datos["estructura"][c] += 1
    datos["estructura"] = dict(datos["estructura"])
    return datos


def contar_2d():
    n = 0
    for o in doc.Objects:
        tid = o.TypeId
        if clase_ifc(o):
            continue
        if tid.startswith(("Part::Part2DObject", "Sketcher::", "App::Annotation", "Draft")) \
                or (tid == "Part::FeaturePython" and hasattr(o, "Points")) \
                or (tid == "Part::Feature" and hasattr(o, "Shape") and not o.Shape.Solids and o.Shape.Edges):
            n += 1
    return n


# --------------------------------------------------------------------------
# Ejecución
# --------------------------------------------------------------------------
f_ifc, modo = obtener_ifc_nativo()
if f_ifc is not None:
    datos = extraer_de_ifc(f_ifc)
else:
    datos = extraer_de_freecad()
    modo = "BIM clásico de FreeCAD (objetos Arch/BIM)"

n2d = contar_2d()
hay_bim = bool(datos["muros"] or datos["puertas"] or datos["espacios"] or datos["plantas"])
datos["documento"] = doc.Name
datos["modo_lectura"] = modo if hay_bim else ("plano 2D" if n2d else "NO RECONOCIDO")
datos["diagnostico"] = diagnostico()

calidad = []


def add(estado, aspecto, detalle):
    calidad.append({"estado": estado, "aspecto": aspecto, "detalle": detalle})


if hay_bim:
    add("OK", "Tipo de modelo", f"BIM — {modo}")
elif n2d:
    add("FALTA", "Tipo de modelo",
        f"Plano 2D ({n2d} objetos de dibujo): convertir a BIM (muros, puertas, espacios) antes de verificar")
else:
    add("ERROR", "Tipo de modelo",
        "No se ha reconocido ningún elemento BIM ni de dibujo. NO concluir que sea 2D: revisar el "
        "DIAGNÓSTICO (TypeId y clases detectadas). Si es un IFC en modo nativo con elementos sin "
        "desplegar, expandir el árbol o abrirlo en modo 'importar'.")
add("OK" if datos["plantas"] else "FALTA", "Plantas con cota", f"{len(datos['plantas'])}")
add("OK" if datos["espacios"] else "FALTA", "Espacios (IfcSpace / Arch Space)",
    f"{len(datos['espacios'])}" if datos["espacios"] else "Sin espacios: superficies y ocupación aproximadas")
uso = None
for d in datos["edificio"].get("psets", {}).values():
    uso = uso or d.get("OccupancyType")
add("OK" if uso else "FALTA", "Uso del edificio declarado", uso or "No declarado: preguntar al usuario")
add("INCOMPLETO" if datos["puertas"] else "FALTA", "Puertas",
    f"{len(datos['puertas'])} (anchura nominal; confirmar anchura libre de paso)")
fr = sum(1 for m_ in datos["muros"] if m_.get("resistencia_fuego"))
add("OK" if fr else "FALTA", "Resistencia al fuego en muros", f"{fr} de {len(datos['muros'])}")
mat = sum(1 for m_ in datos["muros"] if m_.get("material"))
add("OK" if mat else "FALTA", "Materiales en muros", f"{mat} de {len(datos['muros'])}")
e = datos.get("estructura", {})
port = sum(1 for m_ in datos["muros"] if m_.get("portante"))
add("OK" if (e.get("IfcColumn") or e.get("IfcBeam") or port) else ("INCOMPLETO" if e.get("IfcSlab") else "FALTA"),
    "Estructura", f"{e}; muros portantes: {port}")
add("INFO", "Escaleras / PCI", f"{len(datos['escaleras'])} escaleras · {len(datos['pci'])} elementos PCI")
cab = " ".join(datos.get("descripcion_cabecera", []))
if any(k in cab.lower() for k in ("aproximado", "provisional", "croquis")):
    add("AVISO", "Cabecera del archivo", f"El archivo se declara provisional: «{cab}»")
datos["calidad"] = calidad

print("===DBSI_JSON_INICIO===")
print(json.dumps(datos, ensure_ascii=False, indent=1, default=str))
print("===DBSI_JSON_FIN===")
