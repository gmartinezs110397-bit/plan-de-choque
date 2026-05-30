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

HOJAS_PROXIMOS_A_PERDER = (
    "Próximos a perder",
    "Proximos a perder",
    "PROXIMOS A PERDER",
)

HOJAS_TRAMITES_SECTORES = (
    "Trámites sectores",
    "Tramites sectores",
    "TRAMITES SECTORES",
)

HOJAS_LIQUIDADOS_CON_SALDO = (
    "Liquidados con saldo",
    "Liquidados Con Saldo",
    "LIQUIDADOS CON SALDO",
)

HOJAS_ESTRATEGIAS = (
    "Estrategias",
    "ESTRATEGIAS",
)

# Otras pestañas del Excel Contratos plan de choque — reglas por definir
HOJAS_CONTRATOS_OTRAS: dict[str, str] = {}
