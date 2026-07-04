# Instalar <plugin> en OpenCode

> Template — adaptá `<plugin>`, `<owner>` y las skills listadas; guardalo como
> `.opencode/INSTALL.md` en el repo del plugin y linkealo desde el README.

## Prerequisitos

- [OpenCode.ai](https://opencode.ai) instalado
<!-- + lo que tus hooks necesiten (python3, node, etc.) -->

## Instalación (plugin manager nativo)

Agregá el plugin al array `plugin` de tu `opencode.json` (global
`~/.config/opencode/opencode.json` o por proyecto):

```json
{
  "plugin": ["<plugin>@git+https://github.com/<owner>/<plugin>.git"]
}
```

Reiniciá OpenCode. El plugin se instala por el plugin manager de OpenCode y
registra sus skills automáticamente (hook `config` — sin symlinks ni
`skills.paths` manuales).

Verificá listando con el tool `skill` nativo.

### Pinear una versión

```json
{
  "plugin": ["<plugin>@git+https://github.com/<owner>/<plugin>.git#vX.Y.Z"]
}
```

## Uso

Las capacidades son **skills**: usá el tool `skill` nativo de OpenCode para
listarlas y cargarlas.

<!-- Listá acá las skills principales del plugin y qué hace cada una. -->

## Actualizar

OpenCode instala por spec git. Algunas versiones de OpenCode/Bun pinean esa
dependencia en lockfile o cache, así que un restart puede no traer el último
commit. Si no ves la actualización, limpiá el cache de paquetes de OpenCode o
reinstalá el plugin.

## Troubleshooting

1. **El plugin no carga** — `opencode run --print-logs "hola" 2>&1 | grep -i <plugin>`;
   verificá la línea `plugin` de tu `opencode.json`.
2. **Skills no aparecen** — listá con el tool `skill`; si falta todo, el plugin
   no está cargando (punto 1).
