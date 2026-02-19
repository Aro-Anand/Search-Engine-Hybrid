"""
Admin endpoints for the API.

This module contains administrative endpoints for system management.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.search import RetrainResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _load_and_tag(file_path: str, post_type: str) -> List[Dict[str, Any]]:
    """Load a JSON data file and tag each record with post_type."""
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Data file not found: {file_path}")
        return []
    
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    
    for record in data:
        record['post_type'] = post_type
    
    return data


@router.post("/retrain", response_model=RetrainResponse)
async def retrain_search_engine(request: Request):
    """
    Force a complete reload of all data and re-indexing of the search engine.
    
    This endpoint:
    1. Reloads all data from listings.json, blogs.json, and pages.json
    2. Tags each record with its post_type
    3. Re-generates all embeddings
    4. Rebuilds the autocomplete index
    
    **Returns:**
    - Status and count of reloaded items
    """
    try:
        # Reload all data sources
        listings_data = _load_and_tag("data/listings.json", "listing")
        blogs_data = _load_and_tag("data/blogs.json", "blog")
        pages_data = _load_and_tag("data/pages.json", "page")
        
        all_data = listings_data + blogs_data + pages_data
        
        if not all_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data files found or all files are empty"
            )
        
        logger.info(
            f"Retraining with {len(all_data)} items "
            f"({len(listings_data)} listings, {len(blogs_data)} blogs, {len(pages_data)} pages)"
        )
        
        # Re-index all data
        request.app.state.search_engine.index_listings(all_data)
        
        # Rebuild autocomplete
        request.app.state.autocomplete.build_from_listings(all_data)
        
        logger.info(f"Retrain complete. Indexed {len(all_data)} items")
        
        return RetrainResponse(
            status="success",
            message=f"Search engine retrained with {len(listings_data)} listings, {len(blogs_data)} blogs, {len(pages_data)} pages",
            listings_count=len(all_data)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retrain error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Retrain failed")
