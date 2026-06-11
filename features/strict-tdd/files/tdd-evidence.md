# Evidencia TDD — <unidad de trabajo>

| Unidad | RED (test antes) | GREEN (pasa) | TRIANGULATE (casos = escenarios) | SAFETY NET (regresión) | REFACTOR |
|---|---|---|---|---|---|
| <nombre> | ✅ `test_x.py:12` | ✅ runner OK | ✅ 3/3 escenarios | ✅ suite previa verde | ✅ |

## Comando de verificación
```
<test_command>      # debe correrse de verdad, no asumirse
```

## Auditoría de assertions
- [ ] Sin tautologías (`expect(true).toBe(true)`)
- [ ] Sin loops que nunca iteran
- [ ] Cada test afirma comportamiento observable, no detalle de implementación
- [ ] Mocks con verificación de llamada
