"""Constantes compartidas (evita errores de importación por caché desactualizado)."""

COL_DESEMPATE_MANUAL = "Desempate manual"

# Hoja donde se cruza Matriz → Contratos (el nombre varía según plantilla)
HOJAS_CRUCE_CXP = (
    "Cps por depurar",
    "Caja por depurar",
)

HOJAS_SUSPENDIDOS = (
    "Suspendidos",
    "SUSPENDIDOS",
)

# Otras pestañas del Excel Contratos plan de choque — reglas por definir
HOJAS_CONTRATOS_OTRAS: dict[str, str] = {
    # "Próximos a perder", "Trámites sectores", …
}
