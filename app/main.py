"""
Semantic Search API - Main Application

FastAPI application providing REST endpoints for hybrid semantic search.

Author: Development Team
Version: 1.0.0
"""

import logging
import time
import json
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.search_engine import HybridSearchEngine
from app.core.autocomplete import AutocompleteEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Semantic Search API",
    description="Hybrid keyword + semantic search engine for small-scale datasets",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize search engine on startup."""
    logger.info("Starting Semantic Search API...")
    
    app.state.start_time = time.time()
    
    # Initialize search engine
    logger.info("Initializing search engine...")
    engine = HybridSearchEngine(model_name='all-MiniLM-L6-v2')
    
    # Load listings from JSON file
    data_path = Path("data/listings.json")
    
    if not data_path.exists():
        logger.warning(f"Data file not found: {data_path}")
        logger.warning("Creating sample data...")
        
        # Create sample data
        sample_listings = [
            {
                "id": "1",
                "title": "Gaming Laptop - High Performance",
                "description": "Powerful laptop for gaming and creative work",
                "category": "Electronics",
                "price": 1299.99,
                "tags": ["laptop", "gaming", "computer"]
            },
            {
                "id": "2",
                "title": "Wireless Mouse - Ergonomic",
                "description": "Comfortable wireless mouse for everyday use",
                "category": "Electronics",
                "price": 29.99,
                "tags": ["mouse", "wireless", "accessory"]
            },
            {
                "id": "3",
                "title": "Mechanical Keyboard - RGB",
                "description": "Premium mechanical keyboard with RGB lighting",
                "category": "Electronics",
                "price": 149.99,
                "tags": ["keyboard", "mechanical", "gaming"]
            }
        ]
        
        # Ensure data directory exists
        data_path.parent.mkdir(exist_ok=True)
        
        # Save sample data
        with open(data_path, 'w') as f:
            json.dump(sample_listings, f, indent=2)
        
        listings = sample_listings
    else:
        # Load existing data
        with open(data_path) as f:
            listings = json.load(f)
    
    logger.info(f"Loaded {len(listings)} listings")
    
    # Index listings
    engine.index_listings(listings)
    
    # Initialize autocomplete
    logger.info("Building autocomplete index...")
    autocomplete = AutocompleteEngine()
    autocomplete.build_from_listings(listings)
    
    # Store in app state
    app.state.search_engine = engine
    app.state.autocomplete = autocomplete
    app.state.recent_searches = {}  # user_id -> list of recent queries
    
    logger.info("Startup complete!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Semantic Search API...")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Semantic Search API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "search": "/api/v1/search",
            "autocomplete": "/api/v1/autocomplete",
            "recent": "/api/v1/recent",
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
        "version": "1.0.0"
    }


@app.get("/api/v1/search")
async def search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    Search listings with hybrid keyword + semantic matching.
    
    **Parameters:**
    - **q**: Search query string (required)
    - **limit**: Maximum results to return (1-100, default: 10)
    - **offset**: Pagination offset (default: 0)
    
    **Returns:**
    - **query**: The search query
    - **total_results**: Total matching results
    - **results**: List of matching listings with scores
    - **processing_time_ms**: Search latency in milliseconds
    """
    start_time = time.time()
    
    try:
        # Execute search
        results = app.state.search_engine.search(q, top_k=limit + offset)
        
        # Apply pagination
        paginated_results = results[offset:offset + limit]
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Search: query='{q}', results={len(paginated_results)}, "
            f"time={processing_time:.2f}ms"
        )
        
        return {
            "query": q,
            "total_results": len(results),
            "results": paginated_results,
            "processing_time_ms": round(processing_time, 2)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed")


@app.get("/api/v1/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=1, max_length=50, description="Partial query"),
    limit: int = Query(5, ge=1, le=10, description="Max suggestions")
):
    """
    Get autocomplete suggestions for partial query.
    
    **Parameters:**
    - **q**: Partial query string (required)
    - **limit**: Maximum suggestions (1-10, default: 5)
    
    **Returns:**
    - **suggestions**: List of suggested terms
    """
    try:
        suggestions = app.state.autocomplete.suggest(q, limit=limit)
        
        return {
            "query": q,
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"Autocomplete error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Autocomplete failed")


@app.post("/api/v1/recent")
async def add_recent_search(
    user_id: str = Query(..., min_length=1),
    query: str = Query(..., min_length=1)
):
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
        raise HTTPException(status_code=500, detail="Failed to record search")


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
async def not_found_handler(request: Request, exc: HTTPException):
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
        port=8000,
        reload=True,
        log_level="info"
    )
