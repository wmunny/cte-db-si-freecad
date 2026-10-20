#!/usr/bin/env python3
"""
Extrae de un archivo IFC los datos necesarios para verificar el CTE DB-SI
y evalúa la calidad del modelo para esa verificación.

Uso:
    python ifc_extraer.py modelo.ifc            # resumen legible
    python ifc_extraer.py modelo.ifc --json     # salida JSON completa

Requisitos: pip install ifcopenshell numpy
Todas las longitudes se devuelven en metros y las áreas en m².
"""
import argparse
import json
import sys

try:
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as ue
    import ifcopenshell.util.unit as uu
    import numpy as np
except ImportError:
    sys.exit("Falta IfcOpenShell. Instálalo con:  pip install ifcopenshell numpy")


def _bbox(settings, elem):
    """Caja envolvente en coordenadas globales (m) o None si no hay geometría."""
    try:
        shape = ifcopenshell.geom.create_shape(settings, elem)
        v = np.array(shape.geometry.verts).reshape(-1, 3)
        mn, mx = v.min(0), v.max(0)
        return [round(float(x), 3) for x in (*mn, *mx)]
    except Exception:
        return None


def _psets(elem):
    try:
        ps = ue.get_psets(elem)
        for d in ps.values():
            d.pop("id", None)
        return ps
    except Exception:
        return {}


def _prop(psets, name):
    """Busca una propiedad por nombre en cualquier pset."""
    for d in psets.values():
        if name in d and d[name] not in (None, ""):
            return d[name]
    return None


def _storey(elem):
    try:
        c = ue.get_container(elem)
        return c.Name if c else None
    except Exception:
        return None


def extraer(path):
    f = ifcopenshell.open(path)
    scale = uu.calculate_unit_scale(f)  # unidades del archivo -> m
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)

    out = {"archivo": path, "esquema": f.schema}
    hdr = f.header
    try:
        out["descripcion_cabecera"] = list(hdr.file_description.description)
        out["aplicacion_origen"] = hdr.file_name.originating_system
    except Exception:
        pass

    bld = f.by_type("IfcBuilding")
    out["edificio"] = {
        "nombre": bld[0].Name if bld else None,
        "psets": _psets(bld[0]) if bld else {},
    }

    out["plantas"] = [
        {"nombre": st.Name,
         "cota_m": round(float(st.Elevation) * scale, 3) if st.Elevation is not None else None}
        for st in f.by_type("IfcBuildingStorey")
    ]

    espacios = []
    for sp in f.by_type("IfcSpace"):
        ps = _psets(sp)
        area = _prop(ps, "NetFloorArea") or _prop(ps, "GrossFloorArea")
        bb = _bbox(s, sp)
        if area is None and bb:
            area = (bb[3] - bb[0]) * (bb[4] - bb[1])  # aproximación por caja
            origen_area = "caja envolvente (aprox.)"
        else:
            origen_area = "Qto/Pset"
        espacios.append({
            "nombre": sp.Name, "nombre_largo": sp.LongName,
            "tipo": getattr(sp, "PredefinedType", None),
            "planta": _storey(sp),
            "area_m2": round(float(area), 2) if area is not None else None,
            "origen_area": origen_area, "bbox": bb,
            "uso": _prop(ps, "OccupancyType") or _prop(ps, "Category"),
            "ocupacion_declarada": _prop(ps, "OccupancyNumber"),
        })
    out["espacios"] = espacios

    puertas = []
    for d in f.by_type("IfcDoor"):
        ps = _psets(d)
        puertas.append({
            "nombre": d.Name, "planta": _storey(d),
            "ancho_total_m": round(float(d.OverallWidth) * scale, 3) if d.OverallWidth else None,
            "alto_m": round(float(d.OverallHeight) * scale, 3) if d.OverallHeight else None,
            "tipo_operacion": str(getattr(d, "OperationType", None) or ""),
            "salida_emergencia": _prop(ps, "FireExit"),
            "resistencia_fuego": _prop(ps, "FireRating"),
            "bbox": _bbox(s, d),
        })
    out["puertas"] = puertas

    muros = []
    for w in f.by_type("IfcWall"):
        ps = _psets(w)
        bb = _bbox(s, w)
        espesor = None
        if bb:
            espesor = round(min(bb[3] - bb[0], bb[4] - bb[1]), 3)
        muros.append({
            "nombre": w.Name, "planta": _storey(w),
            "espesor_m_aprox": espesor,
            "exterior": _prop(ps, "IsExternal"),
            "portante": _prop(ps, "LoadBearing"),
            "resistencia_fuego": _prop(ps, "FireRating"),
            "material": [m.Name for m in (ue.get_materials(w) or []) if getattr(m, "Name", None)],
            "bbox": bb,
        })
    out["muros"] = muros

    def simple(tipo):
        return [{"nombre": e.Name, "planta": _storey(e), "bbox": _bbox(s, e),
                 "psets": _psets(e)} for e in f.by_type(tipo)]

    out["escaleras"] = simple("IfcStair")
    out["rampas"] = simple("IfcRamp")
    out["ventanas"] = [{"nombre": e.Name, "ancho_m": round(float(e.OverallWidth) * scale, 3) if e.OverallWidth else None,
                        "alto_m": round(float(e.OverallHeight) * scale, 3) if e.OverallHeight else None,
                        "bbox": _bbox(s, e)} for e in f.by_type("IfcWindow")]
    out["pci"] = simple("IfcFireSuppressionTerminal") + simple("IfcAlarm") + simple("IfcSensor")
    out["estructura"] = {t: len(f.by_type(t)) for t in ("IfcColumn", "IfcBeam", "IfcSlab", "IfcRoof", "IfcFooting")}

    # Superficie construida aproximada por planta (caja de muros exteriores o de todos los muros)
    sup = {}
    for m in muros:
        if not m["bbox"]:
            continue
        p = m["planta"] or "?"
        b = sup.setdefault(p, [1e9, 1e9, -1e9, -1e9])
        b[0] = min(b[0], m["bbox"][0]); b[1] = min(b[1], m["bbox"][1])
        b[2] = max(b[2], m["bbox"][3]); b[3] = max(b[3], m["bbox"][4])
    out["superficie_construida_aprox_m2"] = {p: round((b[2] - b[0]) * (b[3] - b[1]), 2) for p, b in sup.items()}

    out["calidad"] = evaluar_calidad(out)
    return out


def evaluar_calidad(d):
    """Lista de comprobaciones de aptitud del modelo para verificar el DB-SI."""
    q = []

    def add(estado, aspecto, detalle):
        q.append({"estado": estado, "aspecto": aspecto, "detalle": detalle})

    add("OK" if d["plantas"] else "FALTA", "Plantas con cota",
        f"{len(d['plantas'])} planta(s)" if d["plantas"] else "Sin IfcBuildingStorey: no se puede calcular la altura de evacuación")
    if d["espacios"]:
        sin_area = sum(1 for e in d["espacios"] if e["area_m2"] is None)
        sin_uso = sum(1 for e in d["espacios"] if not (e["uso"] or e["nombre_largo"] or e["nombre"]))
        add("OK" if not sin_area else "INCOMPLETO", "Espacios (IfcSpace)",
            f"{len(d['espacios'])} espacios; {sin_area} sin área; {sin_uso} sin nombre/uso")
    else:
        add("FALTA", "Espacios (IfcSpace)",
            "No hay espacios: superficies útiles y ocupación deberán deducirse de los muros (aproximado)")
    uso = _prop(d["edificio"]["psets"], "OccupancyType")
    add("OK" if uso else "FALTA", "Uso del edificio declarado",
        uso or "Sin OccupancyType en el edificio: preguntar el uso al usuario")
    if d["puertas"]:
        fe = sum(1 for p in d["puertas"] if p["salida_emergencia"] is not None)
        add("OK" if fe else "INCOMPLETO", "Puertas", f"{len(d['puertas'])} puertas; anchura nominal (no libre); "
            f"{fe} con FireExit")
    else:
        add("FALTA", "Puertas", "Sin IfcDoor")
    fr = sum(1 for m in d["muros"] if m["resistencia_fuego"])
    add("OK" if fr else "FALTA", "Resistencia al fuego (FireRating)",
        f"{fr} de {len(d['muros'])} muros con FireRating")
    e = d["estructura"]
    portantes = sum(1 for m in d["muros"] if m["portante"])
    if e["IfcColumn"] or e["IfcBeam"] or portantes:
        est_estado = "OK"
    elif e["IfcSlab"] or e["IfcRoof"]:
        est_estado = "INCOMPLETO"  # sólo forjados/cubierta: no hay sistema portante vertical
    else:
        est_estado = "FALTA"
    add(est_estado, "Estructura", f"{e}; muros portantes: {portantes}")
    mat = sum(1 for m in d["muros"] if m["material"])
    add("OK" if mat else "FALTA", "Materiales", f"{mat} de {len(d['muros'])} muros con material")
    add("INFO", "Escaleras/rampas", f"{len(d['escaleras'])} escaleras, {len(d['rampas'])} rampas")
    add("INFO", "Instalaciones PCI modeladas", f"{len(d['pci'])} elementos")
    desc = " ".join(d.get("descripcion_cabecera", []))
    if any(k in desc.lower() for k in ("aproximado", "provisional", "croquis")):
        add("AVISO", "Cabecera del archivo", f"El propio archivo se declara provisional: «{desc}»")
    return q


def resumen(d):
    L = [f"Archivo: {d['archivo']}  ({d['esquema']})"]
    L.append(f"Edificio: {d['edificio']['nombre']}")
    L.append("Plantas: " + ", ".join(f"{p['nombre']} (z={p['cota_m']} m)" for p in d["plantas"]))
    L.append(f"Superficie construida aprox.: {d['superficie_construida_aprox_m2']}")
    L.append(f"\nEspacios ({len(d['espacios'])}):")
    for e in d["espacios"]:
        L.append(f"  - {e['nombre']} / {e['nombre_largo']} | {e['area_m2']} m² ({e['origen_area']}) | uso={e['uso']}")
    L.append(f"\nPuertas ({len(d['puertas'])}):")
    for p in d["puertas"]:
        L.append(f"  - {p['nombre']} | ancho {p['ancho_total_m']} m | {p['tipo_operacion']} | "
                 f"FireExit={p['salida_emergencia']} | FireRating={p['resistencia_fuego']}")
    L.append(f"\nMuros ({len(d['muros'])}):")
    for m in d["muros"]:
        L.append(f"  - {m['nombre']} | e≈{m['espesor_m_aprox']} m | ext={m['exterior']} | "
                 f"portante={m['portante']} | FR={m['resistencia_fuego']} | mat={m['material']}")
    L.append(f"\nEscaleras: {len(d['escaleras'])} · Ventanas: {len(d['ventanas'])} · PCI: {len(d['pci'])}")
    for x in d["pci"]:
        L.append(f"  - {x['nombre']} bbox={x['bbox']}")
    L.append("\nCALIDAD DEL MODELO PARA VERIFICAR EL DB-SI:")
    for c in d["calidad"]:
        L.append(f"  [{c['estado']:10s}] {c['aspecto']}: {c['detalle']}")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ifc")
    ap.add_argument("--json", action="store_true", help="salida JSON completa")
    a = ap.parse_args()
    datos = extraer(a.ifc)
    print(json.dumps(datos, ensure_ascii=False, indent=2, default=str) if a.json else resumen(datos))
