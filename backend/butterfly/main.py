"""FastAPI application factory and main entry point."""

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from butterfly.config import settings
from butterfly.db.postgres import create_all_tables, close_db
from butterfly.db.redis import init_redis, close_redis
from butterfly.db.neo4j import init_neo4j, close_neo4j, init_constraints
from butterfly.logging_utils import setup_logging


def create_app() -> FastAPI:
    app = FastAPI(
        title="butterfly-effect",
        description="Causal inference engine for cascade effects",
        version="0.1.0",
    )

    # Initialize enhanced logging with colors and timing
    setup_logging(debug=settings.debug)

    origins = [o.strip() for o in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting up butterfly-effect...")

        # Load spaCy model once at startup — zero per-request cost
        try:
            import spacy
            app.state.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded: en_core_web_sm")
        except Exception as e:
            app.state.nlp = None
            logger.warning(f"spaCy unavailable (non-fatal): {e}")

        try:
            await create_all_tables()
        except Exception as e:
            logger.warning(f"DB init warning (non-fatal): {e}")

        try:
            await init_redis()
        except Exception as e:
            logger.warning(f"Redis init warning (non-fatal): {e}")

        try:
            await init_neo4j()
            await init_constraints()
        except Exception as e:
            logger.warning(f"Neo4j init warning (non-fatal): {e}")

        logger.info("butterfly-effect startup complete")

    @app.on_event("shutdown")
    async def shutdown_event():
        await close_db()
        await close_redis()
        await close_neo4j()

    @app.get("/health")
    async def health_check():
        from butterfly.db.postgres import _USE_SQLITE
        from butterfly.db.redis import _client as redis_cl, _using_fake
        from butterfly.db.neo4j import _neo4j_unavailable

        # Check postgres / sqlite
        postgres_ok = False
        try:
            if _USE_SQLITE:
                import aiosqlite, os
                db_path = os.path.join(
                    os.path.dirname(__file__), "..", "data", "butterfly.db"
                )
                async with aiosqlite.connect(db_path) as db:
                    await db.execute("SELECT 1")
                postgres_ok = True
            else:
                from butterfly.db.postgres import engine
                from sqlalchemy import text
                if engine:
                    async with engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))
                    postgres_ok = True
        except Exception:
            pass

        # Check redis / fakeredis
        redis_ok = False
        try:
            if redis_cl:
                await redis_cl.ping()
                redis_ok = True
        except Exception:
            pass

        # Check neo4j
        neo4j_ok = False
        try:
            from butterfly.db.neo4j import neo4j_driver
            if neo4j_driver and not _neo4j_unavailable:
                async with neo4j_driver.session() as session:
                    await session.run("RETURN 1")
                neo4j_ok = True
        except Exception:
            pass

        return {
            "status": "ok",
            "postgres": postgres_ok,
            "postgres_mode": "sqlite" if _USE_SQLITE else "postgres",
            "redis": redis_ok,
            "redis_mode": "fakeredis" if _using_fake else "redis",
            "neo4j": neo4j_ok,
            "neo4j_mode": "memory" if _neo4j_unavailable else "neo4j",
        }

    from butterfly.api.events import router as events_router
    from butterfly.api.analyze import router as analyze_router, router_admin

    app.include_router(events_router)
    app.include_router(analyze_router)
    app.include_router(router_admin)

    logger.info("FastAPI application created successfully")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
