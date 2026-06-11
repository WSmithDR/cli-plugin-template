---
name: <plugin>-propose
description: "Genera una propuesta de acción como archivo .md en proposals/ para revisión humana antes de ejecutar. El usuario aprueba, edita o descarta. NUNCA ejecutar la acción irreversible directamente."
---

# <plugin> — Propose

Gate de aprobación humana. La acción irreversible NUNCA se ejecuta directo: se escribe
primero como propuesta revisable.

## Proceso
1. Construí los campos de la acción.
2. Escribí `proposals/<hash>/<slug>.md` usando `proposal-template.md` (`status: pending`).
3. Mostrá la ruta al usuario para que revise.
4. El usuario:
   - **Aprueba** (`status: approved`) → parseá el archivo y ejecutá la acción real.
   - **Edita** → re-leé los campos actualizados.
   - **Descarta** (`status: discarded`) → el archivo queda como registro.

## Reglas
- La acción real solo corre cuando `status == approved`.
- Los valores de `status` deben estar en `vocabulary.json` (ver feature vocabulary-guardian).
