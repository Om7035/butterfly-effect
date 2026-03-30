"""FastAPI application factory and main entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
import sys

from butterfly.config import settings
from butterfly.db.postgres import create_all_tables, close_db
from butterfly.db.redis import init_redis, close_redis
from butterfly.db.neo4j import init_neo4j, close_neo4j, init_constraints
from butterfly.api.events import router as events_router
from butterfly.api.causal import router as causal_router
from butterfly.api.simulation import router as simulation_router

# Rate limiter (10 req/min for simulation endpoints)
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="butterfly-effect",
        description=(
            "Causal inference engine — run an event, run the counterfactual, "
            "subtract, show the true causal chain with confidence scores."
        ),
        version="0.4.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    )

    # CORS
    origins = [o.strip() for o in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Starting butterfly-effect v0.4.0...")
        try:
            await create_all_tables()
            await init_redis()
            await init_neo4j()
            await init_constraints()
            logger.info("All services initialized")
        except Exception as e:
            logger.error(f"Startup error: {e}")
            raise

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        await close_db()
        await close_redis()
        await close_neo4j()
        logger.info("Shutdown complete")

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Health check — returns status of all backing services."""
        from butterfly.db.postgres import engine as pg_engine
        from butterfly.db.redis import redis_client
        from butterfly.db.neo4j import neo4j_driver
        from sqlalchemy import text as sa_text

        postgres_ok = redis_ok = neo4j_ok = False

        try:
            async with pg_engine.connect() as conn:
                await conn.execute(sa_text("SELECT 1"))
            postgres_ok = True
        except Exception:
            pass

        try:
            if redis_client:
                await redis_client.ping()
            redis_ok = True
        except Exception:
            pass

        try:
            if neo4j_driver:
                async with neo4j_driver.session() as s:
                    await s.run("RETURN 1")
            neo4j_ok = True
        except Exception:
            pass

        return {
            "status": "ok" if all([postgres_ok, redis_ok, neo4j_ok]) else "degraded",
            "version": "0.4.0",
            "postgres": postgres_ok,
            "redis": redis_ok,
            "neo4j": neo4j_ok,
        }

    # Routers
    app.include_router(events_router)
    app.include_router(causal_router)
    app.include_router(simulation_router)

    logger.info("App created — routes registered")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
