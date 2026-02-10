"""
Semantic Search API - Main Application

FastAPI application providing REST endpoints for hybrid semantic search.

Author: Development Team
Version: 2.0.0
"""

import logging
import time
import json
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.services.search_engine import HybridSearchEngine
from app.services.autocomplete import AutocompleteEngine
from app.api.v1.endpoints import search, listings, admin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources."""
    # Startup logic
    logger.info("Starting Franchise Discovery API...")
    
    app.state.start_time = time.time()
    
    # Initialize search engine
    logger.info("Initializing search engine...")
    engine = HybridSearchEngine(model_name='all-MiniLM-L6-v2')
    
    # Load listings from JSON file
    data_path = Path("data/listings.json")
    
    if not data_path.exists():
        logger.error(f"Data file not found: {data_path}")
        listings_data = []
    else:
        # Load existing data
        with open(data_path, encoding='utf-8') as f:
            listings_data = json.load(f)
    
    logger.info(f"Loaded {len(listings_data)} listings")
    
    # Index listings
    if listings_data:
        engine.index_listings(listings_data)
    
    # Initialize autocomplete
    logger.info("Building autocomplete index...")
    autocomplete = AutocompleteEngine()
    if listings_data:
        autocomplete.build_from_listings(listings_data)
    
    # Store in app state
    app.state.search_engine = engine
    app.state.autocomplete = autocomplete
    app.state.recent_searches = {}  # user_id -> list of recent queries
    
    logger.info("Startup complete!")
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down Franchise Discovery API...")


# Create FastAPI app
app = FastAPI(
    title="Franchise Discovery API",
    description="Intelligent franchise search engine with hybrid keyword + semantic discovery",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(listings.router, prefix="/api/v1", tags=["listings"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Franchise Discovery API",
        "version": "2.1.0",
        "status": "running",
        "endpoints": {
            "search": "/api/v1/search",
            "filters": "/api/v1/filters",
            "recommend": "/api/v1/recommend/{franchise_id}",
            "autocomplete": "/api/v1/autocomplete",
            "add_listing": "/api/v1/listings",
            "retrain": "/api/v1/admin/retrain",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns service status, uptime, and key metrics.
    """
    uptime = time.time() - app.state.start_time
    stats = app.state.search_engine.get_stats()
    
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime, 2),
        "indexed_listings": stats['indexed_listings'],
        "total_searches": stats['total_searches'],
        "model_loaded": True,
        "version": "2.1.0"
    }


# Keep legacy endpoints for backward compatibility
@app.post("/api/v1/recent")
async def add_recent_search(user_id: str, query: str):
    """
    Add a search query to user's recent searches.
    
    **Parameters:**
    - **user_id**: User identifier
    - **query**: Search query to record
    """
    try:
        # Initialize user's search history if not exists
        if user_id not in app.state.recent_searches:
            app.state.recent_searches[user_id] = []
        
        searches = app.state.recent_searches[user_id]
        
        # Remove if already exists (to move to front)
        if query in searches:
            searches.remove(query)
        
        # Add to front
        searches.insert(0, query)
        
        # Keep only last 10
        app.state.recent_searches[user_id] = searches[:10]
        
        # Also record in autocomplete for frequency tracking
        app.state.autocomplete.record_search(query)
        
        return {"status": "ok", "message": "Search recorded"}
        
    except Exception as e:
        logger.error(f"Add recent search error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to record search"}
        )


@app.get("/api/v1/recent/{user_id}")
async def get_recent_searches(user_id: str):
    """
    Get user's recent search history.
    
    **Parameters:**
    - **user_id**: User identifier
    
    **Returns:**
    - **user_id**: The user ID
    - **recent_searches**: List of recent queries (max 10)
    """
    searches = app.state.recent_searches.get(user_id, [])
    
    return {
        "user_id": user_id,
        "recent_searches": searches
    }


@app.delete("/api/v1/recent/{user_id}")
async def clear_recent_searches(user_id: str):
    """
    Clear user's recent search history.
    
    **Parameters:**
    - **user_id**: User identifier
    """
    if user_id in app.state.recent_searches:
        del app.state.recent_searches[user_id]
    
    return {"status": "ok", "message": "Search history cleared"}


@app.get("/api/v1/stats")
async def get_stats():
    """
    Get search engine statistics.
    
    **Returns:**
    - Engine statistics and popular search terms
    """
    engine_stats = app.state.search_engine.get_stats()
    popular_terms = app.state.autocomplete.get_popular_terms(limit=10)
    
    return {
        "engine": engine_stats,
        "popular_searches": [
            {"term": term, "frequency": freq}
            for term, freq in popular_terms
        ]
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint does not exist",
            "path": str(request.url.path)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9999,
        reload=True,
        log_level="info"
    )
