"""
Page endpoints for the API.

This module contains endpoints for managing page entries.
"""

import logging
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.search import PageCreate, ListingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


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
        data_path = Path("data/pages.json")
        
        # Load existing pages
        if data_path.exists():
            with open(data_path, encoding='utf-8') as f:
                pages = json.load(f)
        else:
            pages = []
        
        # Check for duplicate ID
        if any(p.get('id') == page_dict['id'] for p in pages):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Page with id '{page_dict['id']}' already exists"
            )
        
        # Add new page to file
        pages.append(page_dict)
        
        # Save back to file
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(pages, f, indent=2, ensure_ascii=False)
        
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
