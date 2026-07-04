# Instalar cli-plugin-template en OpenCode

## Prerequisitos

- [OpenCode.ai](https://opencode.ai) instalado
- `python3` en el PATH (los hooks y el CLI `cpt` son Python)

## Instalación (plugin manager nativo)

Agregá el plugin al array `plugin` de tu `opencode.json` (global
`~/.config/opencode/opencode.json` o por proyecto):

```json
{
  "plugin": ["cli-plugin-template@git+https://github.com/WSmithDR/cli-plugin-template.git"]
}
```

Reiniciá OpenCode. El plugin se instala por el plugin manager de OpenCode y
registra todas las skills del catálogo automáticamente (el hook `config` pushea
el dir de skills del plugin — no hacen falta symlinks ni `skills.paths` manuales).

Verificá preguntando: *"qué skills de plugin-dev tenés?"* o listando con el tool
`skill` nativo.

OpenCode usa su propia instalación. Si también usás Claude Code, Gemini u otro
harness, instalá el plugin por separado en cada uno (ver `README.md`).

### Alternativa: instalación local (repo clonado)

Si tenés el repo clonado y preferís apuntar OpenCode a esa copia (los cambios
locales aplican sin reinstalar):

```bash
bash bin/install-opencode.sh            # registra plugin + skills en el config global
bash bin/install-opencode.sh --uninstall
```

### Pinear una versión

```json
{
  "plugin": ["cli-plugin-template@git+https://github.com/WSmithDR/cli-plugin-template.git#v1.20.0"]
}
```

## Uso

Las capacidades son **skills** (no comandos slash). Usá el tool `skill` nativo de
OpenCode para listarlas y cargarlas:

```
use skill tool to load plugin-dev
```

- `plugin-dev` — router; enruta según la intención (auditar, integrar, recomendar, promover).
- `plugin-audit` / `plugin-feature` / `plugin-recommend` / `plugin-promote`
- `plugin-register` / `plugin-feedback-log` / `plugin-hotpatch` / `plugin-growth` — ciclo de
  evolución: alta en el registry, captura de fricción, parcheo cross-repo, dashboard.

Las skills nombran tools de Claude Code (`Skill`, `Task`, `Read`, `Edit`); la traducción a
OpenCode está en `skills/plugin-dev/references/tool-mapping.md` (el bootstrap del plugin
ya la referencia).

## Stop hook (feedbacks pendientes + fricción)

Al cerrar la sesión, el plugin corre el Stop hook universal
(`bin/hooks/detect-pending-feedback.py`): reporta feedbacks sin aplicar y, si el host
provee un transcript vía la env var `CPT_TRANSCRIPT_PATH`, detecta fricción nueva y
sugiere cosecharla con el subagente `feedback-harvester`.

## Actualizar

OpenCode instala por spec git. Algunas versiones de OpenCode/Bun pinean esa
dependencia en lockfile o cache, así que un restart puede no traer el último commit.
Si no ves la actualización, limpiá el cache de paquetes de OpenCode o reinstalá el plugin.

## Troubleshooting

1. **El plugin no carga** — `opencode run --print-logs "hola" 2>&1 | grep -i cli-plugin-template`;
   verificá la línea `plugin` de tu `opencode.json`.
2. **Skills no aparecen** — listá con el tool `skill`; si falta todo, el plugin no está cargando (punto 1).
3. **El Stop hook no reporta** — requiere `python3`; probá a mano:
   `echo '{}' | python3 bin/hooks/detect-pending-feedback.py`.
