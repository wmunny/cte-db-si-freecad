# Instalación en ChatGPT (web y escritorio)

## Requisitos

- Los **Skills** de ChatGPT están disponibles en los planes **Business, Enterprise, Healthcare y Edu**. En Enterprise y Edu puede que un administrador tenga que activarlos (*Permissions & Roles*).
- Los skills **no se sincronizan entre dispositivos**: si usas la app de escritorio (macOS/Windows), instálalo también en ella.

Referencia: [OpenAI Help Center – Skills in ChatGPT](https://help.openai.com/en/articles/20001066)

## Pasos

1. Descarga `cte-db-si-freecad.zip` desde [Releases](https://github.com/wmunny/cte-db-si-freecad/releases).
2. En ChatGPT abre **Plugins → Skills → Create → Upload from your computer**.
3. Sube el `.zip` (o la carpeta, según lo que admita tu versión).
4. Si el skill queda marcado como *Needs Review*, revísalo y apruébalo (o pide a tu administrador que lo haga).

> La documentación de OpenAI no especifica el formato exacto de subida. El skill sigue el formato abierto `SKILL.md` (carpeta con `SKILL.md` + recursos). Si tu versión no lo acepta, usa el plan B.

## Compartir con tu equipo

En un espacio de trabajo puedes compartir el skill con personas o grupos, o publicarlo para todo el workspace (*Plugins → Plugin Directory → Skills → ••• → Share*), según los permisos que haya fijado el administrador. Así cada técnico lo instala desde ChatGPT sin descargarlo de GitHub; GitHub sigue siendo la versión de referencia.

## Plan B (planes sin Skills)

1. Crea un **GPT personalizado** o un **Proyecto**.
2. Sube `SKILL.md` como **archivo de conocimiento** (es demasiado largo para el campo de instrucciones).
3. En las instrucciones escribe, por ejemplo:
   *"Para cualquier verificación del CTE DB-SI sigue estrictamente el procedimiento, las tablas y el formato de informe del archivo SKILL.md."*

## FreeCAD

Para trabajar sobre el modelo vivo, ChatGPT necesita además un servidor MCP de FreeCAD conectado. Ver [freecad-mcp.md](freecad-mcp.md).
