# Instalación en Claude

El skill es la carpeta `cte-db-si-freecad/` (la que contiene `SKILL.md` y `scripts/`).

## Claude (app web y de escritorio)

1. Descarga `cte-db-si-freecad.zip` desde [Releases](https://github.com/wmunny/cte-db-si-freecad/releases).
2. En Claude abre **Configuración → Capacidades → Skills** (el nombre exacto del menú puede variar según la versión de la app).
3. Elige subir un skill y selecciona el `.zip`.
4. Comprueba que aparece **cte-db-si-freecad** y que está activado.

No hace falta invocarlo: se activa cuando pides comprobar un modelo o plano contra el CTE / DB-SI.

## Claude Code

Copia la carpeta del skill en tu directorio de skills:

```bash
# skill personal (todas tus sesiones)
mkdir -p ~/.claude/skills
cp -r cte-db-si-freecad ~/.claude/skills/

# o skill de proyecto (sólo en ese repositorio)
mkdir -p .claude/skills
cp -r cte-db-si-freecad .claude/skills/
```

## Actualizar

Descarga la nueva versión desde Releases y vuelve a subirla (sustituye a la anterior). Consulta `CHANGELOG.md` para ver qué ha cambiado.
