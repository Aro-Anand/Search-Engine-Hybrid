"""
Blog endpoints for the API.

This module contains endpoints for managing blog entries.
"""

import logging
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.search import BlogCreate, ListingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


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
        data_path = Path("data/blogs.json")
        
        # Load existing blogs
        if data_path.exists():
            with open(data_path, encoding='utf-8') as f:
                blogs = json.load(f)
        else:
            blogs = []
        
        # Check for duplicate ID
        if any(b.get('id') == blog_dict['id'] for b in blogs):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Blog with id '{blog_dict['id']}' already exists"
            )
        
        # Add new blog to file
        blogs.append(blog_dict)
        
        # Save back to file
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(blogs, f, indent=2, ensure_ascii=False)
        
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
