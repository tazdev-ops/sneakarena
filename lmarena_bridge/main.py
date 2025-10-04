"""
Main FastAPI application for LMArena Bridge.
This is the entry point for the API server.
"""

import sys
import argparse
import uvicorn
import logging
import asyncio
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import load_settings
from .logging_config import setup_logging
from .api.routes_internal import router as internal_router
from .api.routes_models import router as models_router  
from .api.routes_chat import router as chat_router


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    # Load settings
    settings = load_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title="LMArena Bridge API",
        description="OpenAI-compatible API bridge for LMArena",
        version=settings.version,
        docs_url="/docs",  # Enable Swagger docs
        redoc_url="/redoc",  # Enable ReDoc
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, be more restrictive
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(internal_router)
    app.include_router(models_router)
    app.include_router(chat_router)
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        """Tasks to run when the application starts."""
        print(f"LMArena Bridge v{settings.version} starting up...")
        logging.info(f"LMArena Bridge v{settings.version} started successfully")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Tasks to run when the application shuts down."""
        logging.info("LMArena Bridge shutting down...")
    
    @app.get("/")
    async def root():
        """Root endpoint providing basic info about the API."""
        return {
            "message": "LMArena Bridge API",
            "version": settings.version,
            "status": "running",
            "endpoints": {
                "openai_models": "/v1/models",
                "openai_chat": "/v1/chat/completions",
                "health": "/internal/healthz",
                "docs": "/docs"
            }
        }
    
    return app


def cli():
    """
    Command-line interface entry point.
    """
    parser = argparse.ArgumentParser(description="LMArena Bridge API Server")
    parser.add_argument(
        "--host", 
        type=str, 
        default=None,
        help="Host to bind to (defaults to server_host from config)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=None,
        help="Port to bind to (defaults to server_port from config)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Log to file instead of stdout"
    )
    
    args = parser.parse_args()
    
    # Load settings
    settings = load_settings()
    
    # Use command line args or fallback to settings
    host = args.host or settings.server_host
    port = args.port or settings.server_port
    
    # Setup logging
    setup_logging(debug=args.debug, log_file=args.log_file)
    
    # Get the app
    app = create_app()
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="debug" if args.debug else "info",
        reload=False,  # Don't enable reload in production
    )


if __name__ == "__main__":
    cli()