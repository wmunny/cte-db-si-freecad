# Flujo de trabajo recomendado

## ¿De qué archivo parto?

| Tengo… | Recomendación |
|---|---|
| **Proyecto en FreeCAD (.FCStd) modelado en BIM** (muros, puertas, espacios) | Trabajar **directamente sobre el FCStd** con el asistente conectado por MCP. Sin conversiones intermedias y pudiendo corregir en el mismo sitio. |
| **Proyecto en FreeCAD (.FCStd) dibujado en 2D** (líneas, Draft, DXF importado) | Convertirlo **primero a BIM** (muros, puertas, espacios) en FreeCAD; el asistente puede ayudar. Exportar a IFC un plano 2D no crea información. |
| **Archivo IFC** (de Revit, ArchiCAD, FreeCAD, Blender/Bonsai…) | Leerlo **directamente** con `ifc_extraer.py`. No hace falta FreeCAD para verificar. |
| **Sólo DXF/DWG** | Funciona, pero con muchos supuestos. Preparar capas (muros, puertas, recintos como polilíneas cerradas con su uso, cotas de planta, recorridos en capa `EVACUACION`) o, mejor, pasar a BIM. |

## Ciclo

```
 ┌─────────────┐    ┌─────────────────┐    ┌──────────────┐    ┌───────────────┐
 │ 1. Calidad  │ →  │ 2. Verificación │ →  │ 3. Corrección │ →  │ 4. Exportar   │
 │ del modelo  │    │   SI 1 … SI 6   │    │  en FreeCAD   │    │  IFC final    │
 └─────────────┘    └─────────────────┘    └──────┬───────┘    └──────┬────────┘
                             ↑                    │                   │
                             └──── re-verificar ──┘     (opcional: verificar
                                                         el IFC como contraste)
```

1. **Calidad del modelo**: el asistente ejecuta el script de extracción y muestra qué datos hay y cuáles faltan.
2. **Verificación**: completa con tus respuestas lo que el modelo no contiene y emite el informe.
3. **Corrección**: en FreeCAD (a mano o pidiéndoselo al asistente vía MCP).
4. **Exportación**: IFC como entregable.

## Exportar IFC desde tu programa BIM: lista de control

- [ ] Exportar **espacios** (`IfcSpace`) — a menudo desactivado por defecto.
- [ ] Cada espacio con **nombre/uso** reconocible (Aula, Oficina, Almacén…).
- [ ] **Plantas** con su cota.
- [ ] Exportar los **conjuntos de propiedades** estándar (`Pset_*Common`): `FireRating`, `FireExit`, `IsExternal`, `LoadBearing`.
- [ ] Indicar el **uso del edificio** (`OccupancyType`) si el programa lo permite.
