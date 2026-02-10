"""
Listings endpoints for the API.

This module contains endpoints for managing listings.
"""

import logging
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.search import ListingCreate, ListingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/listings", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def add_listing(
    request: Request,
    listing: ListingCreate
):
    """
    Add a new franchise listing to the database and update the search index.
    
    **Parameters:**
    - **listing**: Franchise listing data (id, title, description, sector, location, investment_range, tags)
    
    **Returns:**
    - The created franchise listing
    """
    try:
        # Convert Pydantic model to dict
        listing_dict = listing.model_dump()
        
        # Persist to JSON file - CHECK FOR DUPLICATES FIRST
        data_path = Path("data/listings.json")
        
        # Load existing listings
        if data_path.exists():
            with open(data_path, encoding='utf-8') as f:
                listings = json.load(f)
        else:
            listings = []
        
        # Check for duplicate ID BEFORE modifying in-memory state
        if any(l.get('id') == listing_dict['id'] for l in listings):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Franchise listing with id '{listing_dict['id']}' already exists"
            )
        
        # Add new listing to file
        listings.append(listing_dict)
        
        # Save back to file
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(listings, f, indent=2, ensure_ascii=False)
        
        # Now update in-memory search engine (after successful file write)
        request.app.state.search_engine.add_listing(listing_dict)
        
        # Also update autocomplete
        request.app.state.autocomplete.add_term(listing_dict.get('title', ''))
        
        logger.info(f"Added new franchise listing: {listing_dict['id']}")
        
        return ListingResponse(**listing_dict)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Add listing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add franchise listing")

