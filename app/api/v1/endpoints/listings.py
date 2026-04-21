"""
Listings endpoints for the API.

This module contains endpoints for managing listings.
"""

import logging
import json
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.search import ListingCreate, ListingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

DATA_PATH = Path("data/listings.json")


def _atomic_write_json(file_path: Path, data: list) -> None:
    """Write JSON data atomically using temp file + rename to prevent corruption."""
    dir_path = file_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix='.json.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Atomic rename (on same filesystem)
        os.replace(tmp_path, str(file_path))
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _load_listings() -> list:
    """Load listings from JSON file."""
    if DATA_PATH.exists():
        with open(DATA_PATH, encoding='utf-8') as f:
            return json.load(f)
    return []


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
        
        # Tag as listing type
        listing_dict['post_type'] = 'listing'
        
        # Validate slug exists since UI will send it
        if not listing_dict.get('slug'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug is required"
            )
        
        # Persist to JSON file - CHECK FOR DUPLICATES FIRST
        listings = _load_listings()
        
        # Check for duplicate ID BEFORE modifying in-memory state
        if any(l.get('id') == listing_dict['id'] for l in listings):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Franchise listing with id '{listing_dict['id']}' already exists"
            )
        
        # Add new listing to file
        listings.append(listing_dict)
        
        # Save atomically
        _atomic_write_json(DATA_PATH, listings)
        
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


@router.put("/listings/{listing_id}", response_model=ListingResponse)
async def update_listing(
    request: Request,
    listing_id: str,
    listing: ListingCreate
):
    """
    Update an existing franchise listing and refresh the search index.
    
    **Parameters:**
    - **listing_id**: ID of the listing to update
    - **listing**: Updated listing data
    
    **Returns:**
    - The updated franchise listing
    """
    try:
        listing_dict = listing.model_dump()
        listing_dict['post_type'] = 'listing'
        
        # Update in JSON file
        listings = _load_listings()
        
        found = False
        for i, l in enumerate(listings):
            if str(l.get('id')) == str(listing_id):
                listings[i] = listing_dict
                found = True
                break
        
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing with id '{listing_id}' not found"
            )
        
        # Save atomically
        _atomic_write_json(DATA_PATH, listings)
        
        # Update in-memory search engine
        updated = request.app.state.search_engine.update_listing(listing_id, listing_dict)
        if not updated:
            # Listing was in file but not in memory (edge case) — trigger retrain
            logger.warning(f"Listing {listing_id} found in file but not in memory index")
        
        # Update autocomplete
        request.app.state.autocomplete.add_term(listing_dict.get('title', ''))
        
        logger.info(f"Updated franchise listing: {listing_id}")
        
        return ListingResponse(**listing_dict)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Update listing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update franchise listing")


@router.delete("/listings/{listing_id}", status_code=status.HTTP_200_OK)
async def delete_listing(
    request: Request,
    listing_id: str
):
    """
    Delete a franchise listing and remove it from the search index.
    
    **Parameters:**
    - **listing_id**: ID of the listing to delete
    
    **Returns:**
    - Confirmation message
    """
    try:
        # Remove from JSON file
        listings = _load_listings()
        
        original_count = len(listings)
        listings = [l for l in listings if str(l.get('id')) != str(listing_id)]
        
        if len(listings) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing with id '{listing_id}' not found"
            )
        
        # Save atomically
        _atomic_write_json(DATA_PATH, listings)
        
        # Remove from in-memory search engine
        request.app.state.search_engine.delete_listing(listing_id)
        
        logger.info(f"Deleted franchise listing: {listing_id}")
        
        return {"status": "ok", "message": f"Listing '{listing_id}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete listing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete franchise listing")

