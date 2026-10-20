# Conexión con FreeCAD mediante MCP

El skill aporta el procedimiento y las tablas del DB-SI. Para que el asistente **lea (o modifique) un modelo abierto en FreeCAD** hace falta un **servidor MCP de FreeCAD** conectado al asistente.

## Qué necesita el skill del servidor MCP

Imprescindible:

- Una herramienta para **ejecutar código Python dentro de FreeCAD** (suele llamarse `execute_code` o similar). Con ella el asistente ejecuta `scripts/freecad_extraer.py`.

Recomendable:

- Listar documentos y objetos (`list_documents`, `get_objects`, `get_object`).
- Capturar la vista (`get_view`) para orientarse visualmente.

## Servidores disponibles

Hay varios servidores MCP de FreeCAD de código abierto. Algunos directorios donde encontrarlos y comparar:

- <https://glama.ai/mcp/servers/integrations/freecad>
- <https://lobehub.com/mcp?q=FreeCAD>

Sigue las instrucciones de instalación del servidor elegido (normalmente: instalar un complemento en FreeCAD, arrancar el servidor desde FreeCAD y registrarlo como conector MCP en Claude o ChatGPT).

## Comprobación rápida

Con FreeCAD abierto y el MCP conectado, pide al asistente:

> *"Ejecuta el inventario del skill DB-SI sobre el documento activo y dime si el modelo es BIM o 2D y qué le falta para verificarlo."*

Debe devolver el bloque **CALIDAD** de `freecad_extraer.py`.

## Seguridad

La ejecución de código da al asistente control total sobre FreeCAD. El skill trabaja en **sólo lectura** salvo que pidas expresamente cambios (crear espacios, dibujar recorridos, marcar incumplimientos). Guarda una copia del `.FCStd` antes de pedir modificaciones.
