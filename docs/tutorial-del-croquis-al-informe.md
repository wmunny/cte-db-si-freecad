# Tutorial: del croquis al informe DB-SI con IA y FreeCAD

Ejercicio pedagógico en tres escenas, probado con **ChatGPT Desktop + MCP de FreeCAD** sobre una oficina de 10 × 20 m (4 despachos, recepción, pasillo, aseos y 3 extintores). Funciona igual con Claude.

**Idea central:** la IA no comprueba el Código Técnico porque le pases el PDF, sino porque **le enseñas la norma con un skill** y le das **un modelo que contiene información** (qué es un muro, una puerta, un recinto y para qué se usa).

## Antes de empezar

1. Instala el skill (ver [instalacion-chatgpt.md](instalacion-chatgpt.md) o [instalacion-claude.md](instalacion-claude.md)).
2. Conecta el MCP de FreeCAD (ver [freecad-mcp.md](freecad-mcp.md)) y comprueba que el asistente puede ejecutar código Python en FreeCAD.
3. **Haz una copia de tu archivo .FCStd.**
4. Abre en FreeCAD el dibujo y usa un **chat nuevo**.

---

## Escena 1 — El dibujo 2D: la IA dice lo que no puede ver

Con el plano 2D (líneas, polilíneas, textos) abierto:

```
Usa el skill de verificación CTE DB-SI sobre el documento activo de FreeCAD. NO verifiques normativa todavía y NO modifiques el modelo.

1. Ejecuta el script de extracción y muéstrame el modo de lectura detectado, el bloque de CALIDAD completo y el bloque de diagnóstico (tipos de objeto y clases encontradas).
2. Describe qué contiene el dibujo desde el punto de vista de la información disponible: líneas, polilíneas abiertas y cerradas, arcos, textos, cotas, bloques y capas o grupos; qué textos aparecen; si hay polilíneas cerradas que puedan ser recintos y sus áreas; si se pueden identificar puertas, muros, salidas y las unidades.
3. Concluye qué comprobaciones del DB-SI se podrían hacer con este dibujo tal como está, cuáles no, y qué haría falta para convertirlo en un modelo BIM verificable.
```

**Resultado obtenido:** modo "plano 2D", todo en FALTA. La IA identifica muros, puertas y extintores *dibujados*, pero explica que para ella son líneas sin significado: no hay recintos con superficie útil, ni puertas con anchura de paso, ni uso declarado. Además encontró y respetó una nota del dibujo que advertía que las cabinas de aseo no tenían puertas representadas.

---

## Escena 2 — Convertir el dibujo en un modelo BIM

En el mismo chat:

```
Ahora convierte este dibujo 2D en un modelo BIM verificable, trabajando sobre una COPIA:

0. Guarda primero el documento como "<Nombre>_BIM.FCStd" y trabaja solo en esa copia. No borres el dibujo 2D: muévelo a un grupo "00 Dibujo 2D original" y ocúltalo.
1. Estructura: crea Emplazamiento, Edificio y una Planta "Planta baja" a cota 0,00 con altura 2.700 mm.
2. Muros: a partir de las piezas del grupo de muros, crea muros BIM de 2.700 mm de altura, respetando sus espesores y los huecos del dibujo. Marca como exteriores los del perímetro.
3. Puertas: crea puertas BIM en los huecos del grupo de puertas (una hoja de 900 mm las interiores, doble de 1.800 mm la salida; 2.100 mm de altura), con el sentido de giro del dibujo.
4. Ventanas: crea ventanas BIM en sus posiciones (antepecho 900 mm, altura 1.200 mm).
5. Espacios: crea un espacio BIM por estancia, delimitado por las caras interiores de los muros. Nombre = rótulo; descripción = uso ("Oficina", "Recepción - zona de atención al público", "Pasillo - circulación", "Aseos").
6. Extintores: un objeto BIM por extintor (Fire Suppression Terminal) con la nota "21A-113B, por confirmar".
7. Fidelidad: NO inventes elementos que el dibujo no tenga (p. ej. puertas de cabinas no dibujadas); déjalo anotado. Señala qué medidas son estimadas.
8. Al terminar: recalcula, muéstrame una captura en planta y en 3D, ejecuta de nuevo el script de extracción y enséñame el bloque de CALIDAD. Todavía no verifiques la normativa.
```

**Resultado obtenido:** 1 planta, 29 muros, 6 puertas, 5 ventanas, 8 espacios y 3 extintores BIM. El agente no inventó las puertas de las cabinas y documentó como "límite virtual" la separación pasillo–recepción en lugar de crear un muro inexistente.

Si el agente se atasca, pídeselo **por partes**: estructura y muros → puertas y ventanas → espacios y extintores.

---

## Escena 3 — La verificación

```
Ahora verifica el cumplimiento del DB-SI con el skill. No modifiques el modelo.

Datos que no están en el modelo (trátalos como USUARIO):
- Uso Administrativo (oficina), sin otros usos. Obra nueva. Edificio exento de una sola planta a nivel de calle, sin sótano.
- Ocupación prevista: 6 trabajadores y hasta 10 visitantes simultáneos.
- Única salida: la puerta doble sur, directa a la acera de la vía pública. Abre hacia el exterior.
- Anchura libre de paso: 0,80 m por hoja en todas las puertas.
- Sin locales de riesgo especial; solo el cuadro general de mando y protección de la oficina en recepción, sin local propio.
- Extintores de polvo ABC 6 kg, eficacia 21A-113B. Sin rociadores, detección, alarma ni BIE.
- Materiales, resistencia al fuego y estructura: no disponibles.

Pide solo lo imprescindible que falte. Emite el informe con el formato del skill y cita apartado y tabla del DB-SI en cada comprobación. Señala las incoherencias del modelo como ERROR DE MODELO, no como incumplimiento.
```

**Resultado obtenido (resumen):**

| Comprobación | Resultado |
|---|---|
| Ocupación de cálculo (SI 3, tabla 2.1) | 37 personas — no se rebaja a las 16 previstas |
| Sector ≤ 2.500 m² (SI 1, tabla 1.1) | CUMPLE (200 m²) |
| Una sola salida ≤ 100 personas (SI 3, tabla 3.1) | CUMPLE |
| Recorrido ≤ 25 m (SI 3, tabla 3.1) | CUMPLE — estimado ≈ 18 m (malla de 0,10 m que evita muros y muebles) |
| Puertas y pasillo (SI 3, tabla 4.1) | CUMPLE (0,80 m; pasillo 2,53 m) |
| Extintores a ≤ 15 m (SI 4, tabla 1.1) | CUMPLE — estimado ≈ 8,8 m |
| Cabinas de aseo | ERROR DE MODELO (sin acceso dibujado) |
| Alarma, detección, BIE, bomberos | NO APLICA |
| Materiales, estructura, herrajes, señalización | NO VERIFICABLE |

Conclusión del informe: *"La ausencia de incumplimientos demostrados no equivale a cumplimiento global acreditado."*

---

## Lecciones

1. **Un dibujo 2D no es verificable**: la IA lo reconoce y lo explica en lugar de inventar.
2. **El modelo BIM es la clave**: espacios con uso, puertas con anchura y plantas con cota.
3. **El skill aporta la norma**: tablas, criterios y formato de informe, con cada cifra citada.
4. **La IA distingue** entre lo que cumple, lo que no, lo que falta y lo que está mal modelado.
5. **El técnico sigue siendo imprescindible**: el informe es orientativo y deja explícito lo que no puede acreditar.

Mismo edificio leído como IFC y como BIM convertido desde 2D → mismos resultados (37 personas, ≈17–18 m de recorrido, ≈8,8 m al extintor), lo que muestra que el procedimiento es reproducible.
