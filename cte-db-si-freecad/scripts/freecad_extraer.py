"""
Extrae del documento activo de FreeCAD los datos para verificar el CTE DB-SI
y evalúa la calidad del modelo. Sólo lectura: no modifica el documento.

Cómo usarlo:
  - Desde un MCP de FreeCAD: pasar el contenido de este archivo a la herramienta
    que ejecuta código Python (p. ej. `execute_code`).
  - A mano: FreeCAD > Ver > Paneles > Consola de Python, y pegarlo, o bien
    Macro > Macros... > ejecutar este archivo.

Imprime un bloque JSON entre las marcas ===DBSI_JSON_INICIO=== y ===DBSI_JSON_FIN===.
FreeCAD trabaja en mm y mm²; aquí todo se convierte a m y m².
Probado: sintaxis. Comprobar en el primer uso con un modelo real (las propiedades
de los objetos BIM pueden variar entre versiones de FreeCAD).
"""
import json

import FreeCAD as App

doc = App.ActiveDocument
if doc is None:
    raise SystemExit("No hay documento activo en FreeCAD")


def mm(v):
    try:
        return round(float(v) / 1000.0, 3)
    except Exception:
        return None


def ifc_tipo(o):
    return str(getattr(o, "IfcType", "") or getattr(o, "IfcRole", "") or "")


def bbox(o):
    try:
        b = o.Shape.BoundBox
        return [round(x / 1000.0, 3) for x in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)]
    except Exception:
        return None


def planta(o):
    for p in getattr(o, "InListRecursive", []):
        if ifc_tipo(p) == "Building Storey":
            return p.Label
    return None


def props_ifc(o):
    d = {}
    try:
        for k, v in dict(getattr(o, "IfcProperties", {}) or {}).items():
            d[k] = v
    except Exception:
        pass
    return d


datos = {"documento": doc.Name, "plantas": [], "espacios": [], "puertas": [], "muros": [],
         "escaleras": [], "ventanas": [], "pci": [], "otros_2d": {}}
tipos_2d = {}

for o in doc.Objects:
    t = ifc_tipo(o)
    tid = o.TypeId
    if t == "Building Storey" or tid.endswith("Floor"):
        datos["plantas"].append({"nombre": o.Label, "cota_m": mm(o.Placement.Base.z),
                                 "altura_m": mm(getattr(o, "Height", 0)) or None})
    elif t == "Space" or o.Name.startswith("Space"):
        datos["espacios"].append({
            "nombre": o.Label, "planta": planta(o),
            "area_m2": round(float(getattr(o, "Area", 0)) / 1e6, 2) if hasattr(o, "Area") else None,
            "tipo": str(getattr(o, "SpaceType", "")), "descripcion": str(getattr(o, "Description", "")),
            "personas": getattr(o, "NumberOfPeople", None), "bbox": bbox(o)})
    elif t == "Door" or (hasattr(o, "Width") and "door" in (o.Label + str(getattr(o, "Preset", ""))).lower()):
        datos["puertas"].append({
            "nombre": o.Label, "planta": planta(o), "ancho_total_m": mm(getattr(o, "Width", None)),
            "alto_m": mm(getattr(o, "Height", None)),
            "anfitrion": [h.Label for h in getattr(o, "Hosts", [])],
            "props_ifc": props_ifc(o), "bbox": bbox(o)})
    elif t == "Window":
        datos["ventanas"].append({"nombre": o.Label, "ancho_m": mm(getattr(o, "Width", None)),
                                  "alto_m": mm(getattr(o, "Height", None)), "bbox": bbox(o)})
    elif t == "Wall":
        mat = getattr(o, "Material", None)
        datos["muros"].append({
            "nombre": o.Label, "planta": planta(o), "espesor_m": mm(getattr(o, "Width", None)),
            "altura_m": mm(getattr(o, "Height", None)), "longitud_m": mm(getattr(o, "Length", None)),
            "material": getattr(mat, "Label", None), "props_ifc": props_ifc(o), "bbox": bbox(o)})
    elif t in ("Stair", "Stair Flight") or tid.endswith("Stairs"):
        datos["escaleras"].append({"nombre": o.Label, "ancho_m": mm(getattr(o, "Width", None)),
                                   "altura_m": mm(getattr(o, "Height", None)),
                                   "peldanos": getattr(o, "NumberOfSteps", None), "bbox": bbox(o)})
    elif t in ("Fire Suppression Terminal", "Alarm", "Sensor") or "extint" in o.Label.lower():
        datos["pci"].append({"nombre": o.Label, "bbox": bbox(o)})
    elif tid.startswith(("Part::Part2DObject", "Sketcher::", "App::Annotation")) or "Draft" in o.Name \
            or tid in ("Part::Feature",):
        tipos_2d[tid] = tipos_2d.get(tid, 0) + 1

datos["otros_2d"] = tipos_2d

# --- Calidad del modelo -------------------------------------------------------
calidad = []
def add(estado, aspecto, detalle):
    calidad.append({"estado": estado, "aspecto": aspecto, "detalle": detalle})

es_bim = bool(datos["muros"] or datos["puertas"] or datos["espacios"])
add("OK" if es_bim else "FALTA", "Tipo de modelo",
    "BIM (objetos Arch/BIM)" if es_bim else
    f"Parece un plano 2D ({sum(tipos_2d.values())} objetos de dibujo): convertir a BIM antes de verificar")
add("OK" if datos["plantas"] else "FALTA", "Plantas con cota", f"{len(datos['plantas'])}")
add("OK" if datos["espacios"] else "FALTA", "Espacios (Arch Space)",
    f"{len(datos['espacios'])}" if datos["espacios"] else "Sin espacios: superficies y ocupación aproximadas")
add("INCOMPLETO" if datos["puertas"] else "FALTA", "Puertas",
    f"{len(datos['puertas'])} (anchura nominal; confirmar anchura libre de paso)")
fr = sum(1 for m in datos["muros"] if any("fire" in k.lower() for k in m["props_ifc"]))
add("OK" if fr else "FALTA", "Resistencia al fuego en muros", f"{fr} de {len(datos['muros'])}")
add("OK" if any(m["material"] for m in datos["muros"]) else "FALTA", "Materiales en muros", "")
datos["calidad"] = calidad

print("===DBSI_JSON_INICIO===")
print(json.dumps(datos, ensure_ascii=False, indent=1, default=str))
print("===DBSI_JSON_FIN===")
