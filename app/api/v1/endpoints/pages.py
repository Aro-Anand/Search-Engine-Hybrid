"""
Page endpoints for the API.

This module contains endpoints for managing page entries.
"""

import logging
import json
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.search import PageCreate, ListingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

DATA_PATH = Path("data/pages.json")


def _atomic_write_json(file_path: Path, data: list) -> None:
    """Write JSON data atomically using temp file + rename to prevent corruption."""
    dir_path = file_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix='.json.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, str(file_path))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _load_pages() -> list:
    """Load pages from JSON file."""
    if DATA_PATH.exists():
        with open(DATA_PATH, encoding='utf-8') as f:
            return json.load(f)
    return []


@router.post("/pages", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def add_page(
    request: Request,
    page: PageCreate
):
    """
    Add a new page entry and update the search index.
    
    **Parameters:**
    - **page**: Page data (id, title, description, sector, tags, slug)
    
    **Returns:**
    - The created page entry
    """
    try:
        # Convert Pydantic model to dict
        page_dict = page.model_dump()
        
        # Ensure post_type is set
        page_dict['post_type'] = 'page'
        
        # Ensure sector defaults to "Page" if not provided
        if not page_dict.get('sector'):
            page_dict['sector'] = 'Page'
        
        # Validate slug exists
        if not page_dict.get('slug'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug is required"
            )
        
        # Persist to pages.json
        pages = _load_pages()
        
        # Check for duplicate ID
        if any(p.get('id') == page_dict['id'] for p in pages):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Page with id '{page_dict['id']}' already exists"
            )
        
        # Add new page to file
        pages.append(page_dict)
        
        # Save atomically
        _atomic_write_json(DATA_PATH, pages)
        
        # Update in-memory search engine
        request.app.state.search_engine.add_listing(page_dict)
        
        # Update autocomplete
        request.app.state.autocomplete.add_term(page_dict.get('title', ''))
        
        logger.info(f"Added new page: {page_dict['id']} - {page_dict['title']}")
        
        return ListingResponse(**page_dict)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Add page error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add page")


@router.put("/pages/{page_id}", response_model=ListingResponse)
async def update_page(
    request: Request,
    page_id: str,
    page: PageCreate
):
    """
    Update an existing page entry and refresh the search index.
    
    **Parameters:**
    - **page_id**: ID of the page to update
    - **page**: Updated page data
    
    **Returns:**
    - The updated page entry
    """
    try:
        page_dict = page.model_dump()
        page_dict['post_type'] = 'page'
        
        if not page_dict.get('sector'):
            page_dict['sector'] = 'Page'
        
        # Update in JSON file
        pages = _load_pages()
        
        found = False
        for i, p in enumerate(pages):
            if str(p.get('id')) == str(page_id):
                pages[i] = page_dict
                found = True
                break
        
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with id '{page_id}' not found"
            )
        
        # Save atomically
        _atomic_write_json(DATA_PATH, pages)
        
        # Update in-memory search engine
        request.app.state.search_engine.update_listing(page_id, page_dict)
        
        # Update autocomplete
        request.app.state.autocomplete.add_term(page_dict.get('title', ''))
        
        logger.info(f"Updated page: {page_id}")
        
        return ListingResponse(**page_dict)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Update page error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update page")


@router.delete("/pages/{page_id}", status_code=status.HTTP_200_OK)
async def delete_page(
    request: Request,
    page_id: str
):
    """
    Delete a page entry and remove it from the search index.
    
    **Parameters:**
    - **page_id**: ID of the page to delete
    
    **Returns:**
    - Confirmation message
    """
    try:
        pages = _load_pages()
        
        original_count = len(pages)
        pages = [p for p in pages if str(p.get('id')) != str(page_id)]
        
        if len(pages) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with id '{page_id}' not found"
            )
        
        # Save atomically
        _atomic_write_json(DATA_PATH, pages)
        
        # Remove from in-memory search engine
        request.app.state.search_engine.delete_listing(page_id)
        
        logger.info(f"Deleted page: {page_id}")
        
        return {"status": "ok", "message": f"Page '{page_id}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete page error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete page")

