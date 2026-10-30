from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI

from app.core.database import create_engine_and_session_factory
from app.core.dependencies import require_password_change
from app.modules.auth.router import router as auth_router
from app.modules.clientes.router import (
    router_clientes,
    router_mis_vehiculos,
    router_vehiculos,
)
from app.modules.health.router import router as health_router
from app.modules.ordenes.router import router_estados_orden, router_ordenes
from app.modules.ordenes.router import router_mis_ordenes
from app.modules.repuestos.router import router_repuestos
from app.modules.usuarios.router import router_eventos, router_usuarios


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestiona el ciclo de vida de la aplicación.

    Arranque: crea el motor async y la fábrica de sesiones y los guarda en
    ``app.state``. No se crean recursos al importar el módulo.
    Apagado: libera el motor con ``dispose()``, incluso si hubo errores.

    El hash ficticio del login no se calcula al arrancar: se resuelve de forma
    perezosa en el primer inicio de sesión con correo inexistente.
    """
    engine, session_factory = create_engine_and_session_factory()
    app.state.engine = engine
    app.state.session_factory = session_factory
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Taller mecánica — API", version="1.0.0", lifespan=lifespan)

# Grupo de rutas abierto (sin autenticación de grupo).
# /auth/* se monta acá con dependencias por ruta: el login, el registro y el
# cierre no exigen sesión, y /auth/yo y /auth/cambiar-password la exigen sin
# pasar por el cambio obligatorio del router protegido (RN-06).
# C-09 monta acá /health/*: las sondas de infraestructura no exigen sesión.
router_abierto = APIRouter(tags=["abierto"])
router_abierto.include_router(auth_router, prefix="/auth")
router_abierto.include_router(health_router)

# Grupo de rutas protegido. El control de cambio obligatorio de contraseña se
# inyecta una sola vez a nivel de router (no por ruta): toda ruta protegida
# responde 401 sin sesión y 403 con cambio pendiente.
# Los changes de dominio montan aquí sus routers: /usuarios/*, /eventos/*,
# /clientes/*, /vehiculos/*, /mis-vehiculos, /repuestos/* y /ordenes/*.
router_protegido = APIRouter(
    tags=["protegido"],
    dependencies=[Depends(require_password_change)],
)
router_protegido.include_router(router_usuarios, prefix="/usuarios")
router_protegido.include_router(router_eventos, prefix="/eventos")
router_protegido.include_router(router_clientes, prefix="/clientes")
router_protegido.include_router(router_vehiculos, prefix="/vehiculos")
router_protegido.include_router(router_mis_vehiculos)
router_protegido.include_router(router_repuestos, prefix="/repuestos")
router_protegido.include_router(router_ordenes, prefix="/ordenes")
router_protegido.include_router(router_mis_ordenes)
router_protegido.include_router(router_estados_orden, prefix="/estados-orden")

app.include_router(router_abierto)
app.include_router(router_protegido)
