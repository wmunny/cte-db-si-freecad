#!/usr/bin/env python3
"""
Dibuja la planta de un IFC (muros, puertas, ventanas, espacios y equipos PCI)
para revisar visualmente el modelo antes de verificar el DB-SI.

Uso:
    python ifc_planta.py modelo.ifc planta.png [--planta "Planta baja"]

Requisitos: pip install ifcopenshell numpy matplotlib
"""
import argparse
import sys

try:
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as ue
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("Faltan dependencias:  pip install ifcopenshell numpy matplotlib")

ESTILO = {
    "IfcSpace": dict(color="#cfe3f5", fill=True, alpha=0.5, z=0),
    "IfcWall": dict(color="black", fill=True, alpha=1.0, z=3),
    "IfcDoor": dict(color="red", fill=False, alpha=0.9, z=4),
    "IfcWindow": dict(color="teal", fill=True, alpha=0.8, z=4),
    "IfcStair": dict(color="orange", fill=False, alpha=0.9, z=2),
    "IfcFireSuppressionTerminal": dict(color="magenta", fill=True, alpha=0.9, z=5),
    "IfcFurniture": dict(color="0.75", fill=False, alpha=0.8, z=1),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ifc")
    ap.add_argument("salida")
    ap.add_argument("--planta", help="nombre de la planta a dibujar (por defecto todas)")
    a = ap.parse_args()

    f = ifcopenshell.open(a.ifc)
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    fig, ax = plt.subplots(figsize=(12, 10))
    for tipo, st in ESTILO.items():
        for e in f.by_type(tipo):
            if a.planta:
                c = ue.get_container(e)
                if not c or c.Name != a.planta:
                    continue
            try:
                forma = ifcopenshell.geom.create_shape(s, e)  # conservar referencia
                v = np.array(list(forma.geometry.verts)).reshape(-1, 3)
                if v.size == 0:
                    continue
            except Exception:
                continue
            mn, mx = v.min(0), v.max(0)
            ax.add_patch(plt.Rectangle((mn[0], mn[1]), mx[0] - mn[0], mx[1] - mn[1],
                                       fill=st["fill"], color=st["color"], alpha=st["alpha"], zorder=st["z"]))
            if tipo in ("IfcDoor", "IfcSpace", "IfcFireSuppressionTerminal", "IfcStair"):
                etiqueta = (e.LongName if tipo == "IfcSpace" and e.LongName else e.Name or "").split("|")[0].strip()
                ax.text((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, etiqueta[:22], fontsize=7,
                        color=st["color"] if tipo != "IfcSpace" else "navy", ha="center", zorder=6)
    ax.set_aspect("equal")
    ax.autoscale()
    ax.grid(True, lw=0.3)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"{a.ifc}  —  rojo: puertas (con barrido)  ·  magenta: PCI  ·  azul: espacios")
    plt.savefig(a.salida, dpi=120, bbox_inches="tight")
    print("Planta guardada en", a.salida)


if __name__ == "__main__":
    main()
