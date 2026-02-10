"""
Admin endpoints for the API.

This module contains administrative endpoints for system management.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.search import RetrainResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/retrain", response_model=RetrainResponse)
async def retrain_search_engine(request: Request):
    """
    Force a complete reload of data and re-indexing of the search engine.
    
    This endpoint:
    1. Reloads all listings from the JSON file
    2. Re-generates all embeddings
    3. Rebuilds the autocomplete index
    
    **Returns:**
    - Status and count of reloaded listings
    """
    try:
        data_path = Path("data/listings.json")
        
        if not data_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data file not found: {data_path}"
            )
        
        logger.info("Starting search engine retrain...")
        
        # Reload search engine from file
        count = request.app.state.search_engine.reload_from_file(str(data_path))
        
        # Rebuild autocomplete from the reloaded listings
        listings = request.app.state.search_engine.listings
        request.app.state.autocomplete.build_from_listings(listings)
        
        logger.info(f"Retrain complete. Indexed {count} listings")
        
        return RetrainResponse(
            status="success",
            message=f"Search engine retrained successfully",
            listings_count=count
        )
        
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Retrain error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Retrain failed")
