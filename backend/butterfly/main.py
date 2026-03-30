"""FastAPI application factory and main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from butterfly.config import settings
from butterfly.db.postgres import create_all_tables, close_db
from butterfly.db.redis import init_redis, close_redis
from butterfly.db.neo4j import init_neo4j, close_neo4j, init_constraints
from butterfly.api.events import router as events_router
from butterfly.api.causal import router as causal_router
from butterfly.api.simulation import router as simulation_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="butterfly-effect",
        description="Causal inference engine for cascade effects",
        version="0.1.0",
    )

    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )

    # CORS middleware
    origins = [origin.strip() for origin in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize database connections on startup."""
        logger.info("Starting up butterfly-effect...")
        try:
            await create_all_tables()
            await init_redis()
            await init_neo4j()
            await init_constraints()
            logger.info("All databases initialized successfully")
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            raise

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Close database connections on shutdown."""
        logger.info("Shutting down butterfly-effect...")
        await close_db()
        await close_redis()
        await close_neo4j()
        logger.info("All databases closed")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from butterfly.db.postgres import engine as pg_engine
        from butterfly.db.redis import redis_client
        from butterfly.db.neo4j import neo4j_driver

        postgres_ok = False
        redis_ok = False
        neo4j_ok = False

        # Check PostgreSQL
        try:
            from sqlalchemy import text as sa_text
            async with pg_engine.connect() as conn:
                await conn.execute(sa_text("SELECT 1"))
            postgres_ok = True
        except Exception as e:
            logger.debug(f"PostgreSQL health check failed: {e}")

        # Check Redis
        try:
            if redis_client:
                await redis_client.ping()
            redis_ok = True
        except Exception as e:
            logger.debug(f"Redis health check failed: {e}")

        # Check Neo4j
        try:
            if neo4j_driver:
                async with neo4j_driver.session() as session:
                    await session.run("RETURN 1")
            neo4j_ok = True
        except Exception as e:
            logger.debug(f"Neo4j health check failed: {e}")

        return {
            "status": "ok" if all([postgres_ok, redis_ok, neo4j_ok]) else "degraded",
            "postgres": postgres_ok,
            "redis": redis_ok,
            "neo4j": neo4j_ok,
        }

    logger.info("FastAPI application created successfully")

    # Register routers
    app.include_router(events_router)
    app.include_router(causal_router)
    app.include_router(simulation_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
