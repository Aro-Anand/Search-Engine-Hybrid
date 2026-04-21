"""
Blog endpoints for the API.

This module contains endpoints for managing blog entries.
"""

import logging
import json
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.search import BlogCreate, ListingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

DATA_PATH = Path("data/blogs.json")


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


def _load_blogs() -> list:
    """Load blogs from JSON file."""
    if DATA_PATH.exists():
        with open(DATA_PATH, encoding='utf-8') as f:
            return json.load(f)
    return []


@router.post("/blogs", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def add_blog(
    request: Request,
    blog: BlogCreate
):
    """
    Add a new blog entry and update the search index.
    
    **Parameters:**
    - **blog**: Blog data (id, title, description, sector, tags, slug)
    
    **Returns:**
    - The created blog entry
    """
    try:
        # Convert Pydantic model to dict
        blog_dict = blog.model_dump()
        
        # Ensure post_type is set
        blog_dict['post_type'] = 'blog'
        
        # Ensure sector defaults to "Blog" if not provided
        if not blog_dict.get('sector'):
            blog_dict['sector'] = 'Blog'
        
        # Validate slug exists
        if not blog_dict.get('slug'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug is required"
            )
        
        # Persist to blogs.json
        blogs = _load_blogs()
        
        # Check for duplicate ID
        if any(b.get('id') == blog_dict['id'] for b in blogs):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Blog with id '{blog_dict['id']}' already exists"
            )
        
        # Add new blog to file
        blogs.append(blog_dict)
        
        # Save atomically
        _atomic_write_json(DATA_PATH, blogs)
        
        # Update in-memory search engine
        request.app.state.search_engine.add_listing(blog_dict)
        
        # Update autocomplete
        request.app.state.autocomplete.add_term(blog_dict.get('title', ''))
        
        logger.info(f"Added new blog: {blog_dict['id']} - {blog_dict['title']}")
        
        return ListingResponse(**blog_dict)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Add blog error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add blog")


@router.put("/blogs/{blog_id}", response_model=ListingResponse)
async def update_blog(
    request: Request,
    blog_id: str,
    blog: BlogCreate
):
    """
    Update an existing blog entry and refresh the search index.
    
    **Parameters:**
    - **blog_id**: ID of the blog to update
    - **blog**: Updated blog data
    
    **Returns:**
    - The updated blog entry
    """
    try:
        blog_dict = blog.model_dump()
        blog_dict['post_type'] = 'blog'
        
        if not blog_dict.get('sector'):
            blog_dict['sector'] = 'Blog'
        
        # Update in JSON file
        blogs = _load_blogs()
        
        found = False
        for i, b in enumerate(blogs):
            if str(b.get('id')) == str(blog_id):
                blogs[i] = blog_dict
                found = True
                break
        
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blog with id '{blog_id}' not found"
            )
        
        # Save atomically
        _atomic_write_json(DATA_PATH, blogs)
        
        # Update in-memory search engine
        request.app.state.search_engine.update_listing(blog_id, blog_dict)
        
        # Update autocomplete
        request.app.state.autocomplete.add_term(blog_dict.get('title', ''))
        
        logger.info(f"Updated blog: {blog_id}")
        
        return ListingResponse(**blog_dict)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Update blog error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update blog")


@router.delete("/blogs/{blog_id}", status_code=status.HTTP_200_OK)
async def delete_blog(
    request: Request,
    blog_id: str
):
    """
    Delete a blog entry and remove it from the search index.
    
    **Parameters:**
    - **blog_id**: ID of the blog to delete
    
    **Returns:**
    - Confirmation message
    """
    try:
        blogs = _load_blogs()
        
        original_count = len(blogs)
        blogs = [b for b in blogs if str(b.get('id')) != str(blog_id)]
        
        if len(blogs) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blog with id '{blog_id}' not found"
            )
        
        # Save atomically
        _atomic_write_json(DATA_PATH, blogs)
        
        # Remove from in-memory search engine
        request.app.state.search_engine.delete_listing(blog_id)
        
        logger.info(f"Deleted blog: {blog_id}")
        
        return {"status": "ok", "message": f"Blog '{blog_id}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete blog error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete blog")

