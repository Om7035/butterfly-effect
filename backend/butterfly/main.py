"""FastAPI application factory and main entry point."""

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from butterfly.api.analyze import router as analyze_router
from butterfly.api.causal import router as causal_router
from butterfly.api.demo import router as demo_router
from butterfly.api.events import router as events_router
from butterfly.api.simulation import router as simulation_router
from butterfly.config import settings
from butterfly.db.neo4j import close_neo4j, init_constraints, init_neo4j, _neo4j_unavailable
from butterfly.db.postgres import close_db, create_all_tables
from butterfly.db.redis import close_redis, init_redis

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

        # Postgres — optional, warn and continue if unavailable
        try:
            await create_all_tables()
        except Exception as e:
            logger.warning(f"Postgres unavailable (running without it): {e}")

        # Redis — falls back to fakeredis automatically
        try:
            await init_redis()
        except Exception as e:
            logger.warning(f"Redis init error: {e}")

        # Neo4j — falls back to in-memory graph automatically
        try:
            await init_neo4j()
            if not _neo4j_unavailable:
                await init_constraints()
        except Exception as e:
            logger.warning(f"Neo4j init error: {e}")

        logger.info("Startup complete — degraded mode if DBs are offline")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        await close_db()
        await close_redis()
        await close_neo4j()
        logger.info("Shutdown complete")

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Health check — returns status of all backing services."""
        from sqlalchemy import text as sa_text

        from butterfly.db.neo4j import neo4j_driver
        from butterfly.db.postgres import engine as pg_engine
        from butterfly.db.redis import redis_client

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
    app.include_router(demo_router)
    app.include_router(analyze_router)

    logger.info("App created — routes registered")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
