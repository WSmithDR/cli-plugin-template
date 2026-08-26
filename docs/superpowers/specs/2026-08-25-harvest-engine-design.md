# Harvest Engine — Diseño

**Fecha:** 2026-08-25
**Estado:** Borrador para revisión

## Objetivo

Cosechar ideas, patrones y hallazgos de los plugins de terceros instalados en el sistema (`.claude`, `.opencode`, `.kiro`, `.agents` — locales y globales), de forma diaria y autónoma, mediante un panel de agentes IA gratuitos que analizan en paralelo, debaten y llegan a consenso. El conocimiento validado se guarda como **learnings** (`cpt learning save`).

**Meta final**: producir un mapa de **homologaciones cross-CLI** (qué concepto de cada CLI equivale a cuál, qué piezas comparten) que permita una arquitectura de **piezas reutilizables** donde el soporte de cada CLI sea solo un **adaptador delgado**.

## Decisiones de diseño (aprobadas por el usuario)

1. **Disparo**: cron diario del sistema (sin abrir ningún CLI).
2. **Modo autónomo**: sin confirmación interactiva; aprobación previa vía configuración.
3. **Sin Claude Code** (de pago). Solo modelos gratuitos e ilimitados (ej. OX Alpha FREE vía opencode).
4. **Análisis multi-modelo con debate** y consenso.
5. **Autoselección de modelos**: el sistema puntúa el desempeño de cada modelo y degrada/reemplaza a los que sean lastre.
6. **Debate sobre homologaciones**, no solo ideas: datos vs piezas, equivalencias entre primitivas de CLIs distintos.

## Arquitectura

```
systemd path unit / fswatch (eventos) ──┐
systemd timer (batch nocturno, fallback) ─┴─> cpt harvest scan
        │  (normaliza cada plugin a un IR canónico versionado;
        │   diff de IR vs snapshot → solo cambios reales)
        ▼
   cola de pendientes (JSON)
                          │
                          ▼
              cpt harvest run (headless)
        homologación EXACTA por hash del IR → sin LLM
        solo lo difuso llega al panel
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   agente A           agente B          agente C     (modelos gratuitos,
   veredictos         veredictos        veredictos    elegidos por scorecard)
        └─────────────────┼─────────────────┘
                          ▼
        CONSENSO = agregación de triples machine-readable
        (claim + evidencia + confianza)
                          ▼
        cpt learning save + homologies.json (mapa de equivalentes)
```

## Componentes

### 1. `cpt harvest scan` (sin LLM, barato)
- **IR canónico**: cada plugin detectado se normaliza a un esquema intermedio versionado único (manifest, skills, hooks/powers, agents, commands — independiente del CLI). El diff contra el snapshot se hace **a nivel de IR**, no de archivos crudos.
- **Trigger por eventos + batch nocturno**: systemd path units (o fswatch) sobre los directorios de CLIs disparan el scan al instante cuando cambia algo (gratis, incremental); un timer nocturno con `Persistent=true` queda como red de seguridad para lo que se haya escapado. Sin cambios → no hay corrida.
- **Autodetección de CLIs** (lista incremental, cero configuración): sondea rutas y binarios conocidos (`~/.claude`, `~/.opencode`, `~/.kiro`, `~/.agents/skills`; binarios `gemini`, `codex`, `copilot`, `crush`, etc.). Cada CLI nuevo detectado se agrega automáticamente al inventario.
- **Sugerencias**: CLI soportado nunca analizado → marcado "sin cosechar" y sugerido. CLI conocido sin plugins → sugerido como candidato a probar.
- Cola de pendientes: `~/.local/share/cli-plugin-template/harvest/pending.json`.

### 1.1 Mecanismos de instalación por CLI (verificado contra docs oficiales)

| CLI | Fuente de verdad del scan | Notas |
|---|---|---|
| Claude Code | `~/.claude/plugins` + marketplaces conocidos | componentes: `commands/`, `hooks/hooks.json`, `agents/`, `skills/` |
| OpenCode | array `plugin` + `skills.paths` en `~/.config/opencode/opencode.json` | npm/git se resuelven a `~/.cache/opencode/node_modules/`; rutas locales se leen directo |
| Gemini CLI | `~/.gemini/extensions/*/gemini-extension.json` | gestión vía `gemini extensions` |
| Kiro | powers instalados (marketplace o GitHub), raíz con `plugin.json` o `POWER.md` | sigue el estándar **Agent Plugins** (`plugin.json` + `skills/` + `mcp.json`) |

> **Hallazgo clave para la meta de arquitectura**: los powers de Kiro implementan el estándar abierto [Agent Plugins](https://agent-plugins.org) (mantenedores de Amazon, Cursor, Microsoft, OpenAI, Vercel): formato vendor-neutral con manifest + Agent Skills. El mapa de homologaciones debe tratar ese estándar como el núcleo común emergente — las piezas reutilizables del template deberían alinearse con él, dejando por-CLI solo el adaptador.

### 2. `cpt harvest run` (análisis LLM)

- Lee la cola, respeta presupuesto (`max_plugins_per_run`, default 3).
- **Homología exacta primero, gratis**: dos piezas con IR isomorfo (hash canónico igual) se homologan sin invocar ningún modelo. El panel LLM solo analiza lo **difuso** (mismo propósito, distinta forma) y los hallazgos cualitativos.
- Por cada plugin que llega al panel: dossier (README, SKILL.md, plugin.json, estructura + código fuente). Reglas anti-ruido:
  - Fuente propia siempre (skills/, hooks/, agents/, commands/, manifests).
  - `node_modules` anidado dentro del plugin = dependencias de terceros → skip.
  - Excepción: en opencode los paquetes instalados residen bajo `~/.cache/opencode/packages/` (ej. superpowers). **La fuente de verdad son las entradas declaradas** en `~/.config/opencode/opencode.json` (array `plugin`, claves `skills.paths`): nombres npm/git se resuelven a su carpeta instalada; rutas locales se leen directo. Nunca escanear `.cache` a ciegas ni descender a dependencias transitivas.
  - Tope de tamaño por dossier para no leer árboles gigantes.
- Despacha N agentes (default 3) **en paralelo** vía CLI headless ya autenticado:
  - Ejecutor principal: `opencode run` con modelos gratuitos/ilimitados (ej. `ox-alpha-free`). Otros ejecutores gratuitos opcionales vía config. **Claude Code excluido por costo.**

### 3. Veredictos y consenso

**Formato atómico**: cada agente no escribe prosa — emite **triples machine-readable**: `{claim, evidence, confidence}` donde `evidence` son como máximo **3 citas exactas** de código/manifests (resúmenes prohibidos: fuerzan evidencia quirúrgica y resisten alucinación).

**Dos dimensiones:**
- **a) Hallazgos generales**: cada agente recibe los triples anonimizados de los otros y emite veredictos `agree` / `refute` (con triple de refutación) / `nueva idea`. El consenso es una **agregación de triples** (umbral configurable: mayoría simple default; `strict` = unanimidad).
- **b) Homologaciones difusas**: mapeo entre primitivas de CLIs distintos (¿qué es dato vs pieza reutilizable?, equivalencias tipo hooks ↔ powers ↔ agents). Salida: entradas `{concepto_a, cli_a, concepto_b, cli_b, confianza, evidencia}` validadas por el mismo umbral → alimentan la meta de núcleo reutilizable + adaptador delgado por CLI.

### 4. Scorecard de modelos (autoselección)
- **Regla dura anti-pago**: los ejecutores solo pueden invocar modelos marcados como **gratuitos/ilimitados** en la lista del CLI. El filtro es a nivel de código (allowlist), no de configuración: un modelo de pago **no puede** ser seleccionado ni como fallback, ni por error de parseo, ni por override del usuario sin una clave explícita `allow_paid: true` que no existirá por defecto.
- **Claude Code excluido por construcción**: el binario no está entre los ejecutores soportados; ningún flujo puede invocarlo.
- **Descubrimiento automático de modelos**: al inicio de cada corrida se ejecuta `opencode models` (o equivalente del executor) y se filtran los modelos gratuitos realmente accesibles con la auth vigente. Nada hardcodeado: modelos nuevos gratuitos que aparecen entran como candidatos; los de pago se descartan en el filtro.
- Si tras el filtro quedan 0 modelos utilizables → la corrida aborta con aviso claro; **nunca** degrada a modelos de pago.
- **Health check**: prompt mínimo de prueba a cada modelo elegido antes del análisis completo; el que falle se reemplaza por otro **gratuito** de la pool y recibe penalización.
- Por cada corrida se registra por modelo: acuerdos logrados, refutaciones correctas (validadas contra consenso final), latencia, fallos/timeouts.
- Un modelo con desempeño bajo sostenido (ej. < umbral de acuerdo útil durante N corridas) se marca `laggard`: baja de la rotación y es reemplazado por otro modelo gratuito de la pool.
- La rotación vive en `harvest/scorecard.json`; overrides manuales posibles por config.

### 5. Persistencia
- Consenso de hallazgos → `cpt learning save` con metadata: plugin origen, modelos participantes, archivos-evidencia.
- Consenso de homologaciones → `homologies.json` versionado (fuente única de verdad del mapa cross-CLI).
- Contested → `harvest/contested.json` para curación manual posterior.
- Snapshot actualizado al finalizar corrida exitosa.

### 6. Configuración (`cli-config.yaml`, feature externalized-config)

**Solo overrides — sin config, todo funciona con autodetección y defaults.**

```yaml
harvest:
  schedule: "0 9 * * *"
  clis:
    exclude: []          # ej. [codex] para ignorar un CLI detectado
    force_include: []    # para CLIs en rutas no estándar
  executor:
    cli: opencode
    # models_pool: SEMILLA OPCIONAL de preferencia; la pool VIVA de modelos
    # se descubre sola (opencode models) y evoluciona en scorecard.json.
    # Nada incremental vive en este yaml.
    panel_size: 3
  consensus_threshold: majority
  max_plugins_per_run: 3
```

El resto (lista de CLIs a escanear, plugins por CLI) lo maneja la autodetección del §1 de forma incremental.

### 7. Instalador de scheduler
- Script idempotente que instala **systemd timer con `Persistent=true`** (Linux): si la PC estaba apagada a la hora programada, la corrida perdida se ejecuta automáticamente al encender.
- Fallback si no hay systemd: chequeo "catch-up" al primer inicio de sesión en cualquier CLI — si pasó más de 24h desde la última corrida, dispara el scan.

## Manejo de errores

- Modelo caído o sin auth → ese agente se salta; si quedan < 2 activos, se aborta esa pasada dejando la cola intacta.
- Plugin ilegible → marcado `failed` en la cola, no bloquea el resto.
- Timeout de un modelo → 1 reintento; si falla, corre con N-1 agentes y penaliza su scorecard.
- Corrida interrumpida → snapshot no se actualiza; reprocesa idempotentemente (hash de contenido).

## Testing

- Fixture de plugin fake: asserts sobre scan/diff, formato de dossier, agregación de consenso (mayoría vs unanimidad), y lógica del scorecard (degradación de laggard con salidas simuladas).

## Fuera de alcance (YAGNI)

- Notificaciones push (curación manual vía `cpt learning list` / plugin-growth).
- Modelos de pago (incluye todo lo de Claude).
- Generación automática de adaptadores a partir del mapa (fase futura; hoy el mapa es documental).

## Fase 2 (anotadas, no implementar ahora)

Del brainstorm extremo (corpus: `harvest-engine cli-plugin-template`), ideas potentes que requieren infraestructura adicional y quedan para una segunda iteración:

- **Round-trip como juez**: homología `confirmed` solo si un shim ida + shim vuelta ejecutan sin pérdida entre CLIs.
- **Canaries sintéticos**: plugins con defectos plantados miden la tasa de detección real de cada modelo → scorecard medible sin juez LLM.
