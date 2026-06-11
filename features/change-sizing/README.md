# Feature: change-sizing

## Qué hace

Mantiene commits y PRs en un tamaño revisable: **commits atómicos** (un comportamiento, con
su código + tests + docs juntos), un **presupuesto de líneas** que avisa antes de un PR
gigante, y **PRs en cadena** cuando el cambio no entra en uno solo.

## Por qué

Un PR de 2000 líneas no se revisa bien — los bugs pasan. Commits atómicos y PRs acotados
bajan la carga cognitiva del reviewer y hacen los rollbacks quirúrgicos.

## Patrones

### Commits atómicos (work-unit)

Cada commit = **un comportamiento completo**, no capas separadas.

- ✅ `feat(auth): add token validation model and tests`
- ❌ `add models` + `add tests` + `add docs` por separado.

Checklist: ¿se puede revertir solo? ¿se entiende standalone? ¿pasa los tests?

### Presupuesto de revisión

Antes de aplicar, sumá `additions + deletions`. Si supera el presupuesto (default ~400
líneas), no hagas un PR único: pasá a cadena.

### PRs en cadena

| Estrategia | Cómo | Cuándo |
|---|---|---|
| **Stacked a main** | PR1→main, PR2 apunta a la historia de PR1, etc. Cada slice mergea en orden | Slices independientes; querés mergear/rollbackear de a uno |
| **Feature branch** | branch `feat/x` tracker; PR1→tracker, PR2→PR1, … ; integra todo al final | El feature debe entrar completo o nada |

Reglas: ≤400 → PR único; >400 + independiente → stacked; >400 + integrado → feature branch;
generado/vendor/migración → pedir excepción al maintainer.

## Integración

1. Al planear tasks (ver `planning-workflow`), estimá el tamaño y elegí estrategia.
2. Hacé commits atómicos por comportamiento.
3. Si superás el presupuesto, armá la cadena e incluí en cada PR su scope + checklist de
   autonomía (CI verde, un entregable, rollback-safe, tests+docs cubiertos).

## Tests

Verificá que un cambio grande dispara la alerta de presupuesto y que cada commit del split
es revertible y entendible por sí solo.

## Changelog

- **1.0.0** — patrones de `gentle-pi` (work-unit-commits, chained-pr, review workload guard).
