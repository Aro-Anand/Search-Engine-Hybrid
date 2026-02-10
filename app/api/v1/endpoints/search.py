"""
Search endpoints for the API.

This module contains endpoints for search and autocomplete functionality.
"""

import logging
import time
from typing import List

from fastapi import APIRouter, Query, HTTPException, Request

from app.schemas.search import (
    SearchResponse, 
    AutocompleteResponse, 
    FiltersResponse,
    RecommendationResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sector: str = Query(None, description="Filter by sector (e.g., 'Food & Beverage')"),
    location: str = Query(None, description="Filter by location"),
    min_investment: int = Query(None, description="Minimum investment in lakhs"),
    max_investment: int = Query(None, description="Maximum investment in lakhs")
):
    """
    Search franchise listings with hybrid keyword + semantic matching.
    
    **Parameters:**
    - **q**: Search query string (required)
    - **limit**: Maximum results to return (1-100, default: 10)
    - **offset**: Pagination offset (default: 0)
    - **sector**: Filter by business sector (optional)
    - **location**: Filter by location (optional)
    - **min_investment**: Minimum investment in lakhs (optional)
    - **max_investment**: Maximum investment in lakhs (optional)
    
    **Returns:**
    - **query**: The search query
    - **total_results**: Total matching results
    - **results**: List of matching franchise listings with scores
    - **processing_time_ms**: Search latency in milliseconds
    """
    start_time = time.time()
    
    try:
        # Execute search
        results = request.app.state.search_engine.search(q, top_k=limit + offset + 100)
        
        # Apply filters
        if sector:
            results = [r for r in results if r.get('sector', '').lower() == sector.lower()]
        
        if location:
            results = [r for r in results if location.lower() in r.get('location', '').lower()]
        
        # Investment range filter
        if min_investment is not None or max_investment is not None:
            filtered_results = []
            for r in results:
                inv_range = r.get('investment_range', '')
                if inv_range:
                    # Extract numbers from investment_range (e.g., "₹10L-₹20L")
                    import re
                    numbers = re.findall(r'(\d+)L', inv_range)
                    if numbers:
                        min_val = int(numbers[0])
                        max_val = int(numbers[-1]) if len(numbers) > 1 else min_val
                        
                        # Check if within range
                        if min_investment is not None and max_val < min_investment:
                            continue
                        if max_investment is not None and min_val > max_investment:
                            continue
                        
                        filtered_results.append(r)
            results = filtered_results
        
        # Apply pagination
        total_results = len(results)
        paginated_results = results[offset:offset + limit]
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Search: query='{q}', filters=(sector={sector}, location={location}), "
            f"results={len(paginated_results)}, time={processing_time:.2f}ms"
        )
        
        return SearchResponse(
            query=q,
            total_results=total_results,
            results=paginated_results,
            processing_time_ms=round(processing_time, 2)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    request: Request,
    q: str = Query(..., min_length=1, max_length=50, description="Partial query"),
    limit: int = Query(5, ge=1, le=10, description="Max suggestions")
):
    """
    Get smart autocomplete suggestions (titles only) using background search.
    
    This endpoint performs a hybrid search in the background and returns 
    the most relevant franchise titles based on the users partial input.
    """
    try:
        # Use the search engine to find related franchises
        # We search for more than limit to ensure we have enough diversity after title extraction
        results = request.app.state.search_engine.search(q, top_k=limit * 2)
        
        # Extract unique titles and preserve order (relevance)
        seen = set()
        suggestions = []
        for r in results:
            title = r.get('title')
            if title and title not in seen:
                suggestions.append(title)
                seen.add(title)
            if len(suggestions) >= limit:
                break
        
        return AutocompleteResponse(
            query=q,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Autocomplete error: {e}", exc_info=True)
        # Fallback to simple Trie suggestions if search fails (optional, but here we just error)
        raise HTTPException(status_code=500, detail="Autocomplete failed")



@router.get("/filters", response_model=FiltersResponse)
async def get_filters(request: Request):
    """
    Get available filter options for franchise search.
    
    **Returns:**
    - **sectors**: List of available business sectors
    - **locations**: List of available locations
    - **investment_ranges**: List of available investment ranges
    """
    try:
        listings = request.app.state.search_engine.listings
        
        # Extract unique values
        sectors = sorted(set(
            listing.get('sector', '') 
            for listing in listings 
            if listing.get('sector')
        ))
        
        locations = sorted(set(
            listing.get('location', '') 
            for listing in listings 
            if listing.get('location')
        ))
        
        investment_ranges = sorted(set(
            listing.get('investment_range', '') 
            for listing in listings 
            if listing.get('investment_range')
        ))
        
        return FiltersResponse(
            sectors=sectors,
            locations=locations,
            investment_ranges=investment_ranges
        )
        
    except Exception as e:
        logger.error(f"Filters error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get filters")


@router.get("/recommend/{franchise_id}", response_model=RecommendationResponse)
async def get_recommendations(
    request: Request,
    franchise_id: str,
    limit: int = Query(5, ge=1, le=20, description="Max recommendations"),
    same_sector: bool = Query(True, description="Only recommend from same sector")
):
    """
    Get franchise recommendations based on similarity.
    
    **Parameters:**
    - **franchise_id**: ID of the franchise to get recommendations for
    - **limit**: Maximum recommendations (1-20, default: 5)
    - **same_sector**: Only recommend franchises from the same sector (default: true)
    
    **Returns:**
    - **franchise_id**: ID of the source franchise
    - **franchise_title**: Title of the source franchise
    - **recommendations**: List of similar franchises
    """
    try:
        listings = request.app.state.search_engine.listings
        embeddings = request.app.state.search_engine.embeddings
        
        # Find the source franchise
        source_franchise = None
        source_index = None
        
        for idx, listing in enumerate(listings):
            if str(listing.get('id')) == str(franchise_id):
                source_franchise = listing
                source_index = idx
                break
        
        if not source_franchise:
            raise HTTPException(status_code=404, detail=f"Franchise {franchise_id} not found")
        
        # Get embedding for source franchise
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        source_embedding = embeddings[source_index].reshape(1, -1)
        
        # Calculate similarities with all other franchises
        similarities = cosine_similarity(source_embedding, embeddings)[0]
        
        # Create list of (index, similarity) tuples, excluding the source
        candidates = [
            (idx, sim) 
            for idx, sim in enumerate(similarities) 
            if idx != source_index
        ]
        
        # Filter by sector if requested
        if same_sector and source_franchise.get('sector'):
            source_sector = source_franchise.get('sector', '').lower()
            candidates = [
                (idx, sim) 
                for idx, sim in candidates 
                if listings[idx].get('sector', '').lower() == source_sector
            ]
        
        # Sort by similarity (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Get top recommendations
        recommendations = []
        for idx, sim in candidates[:limit]:
            rec = listings[idx].copy()
            rec['score'] = float(sim)
            rec['semantic_score'] = float(sim)
            rec['match_type'] = 'semantic'
            recommendations.append(rec)
        
        return RecommendationResponse(
            franchise_id=franchise_id,
            franchise_title=source_franchise.get('title', ''),
            recommendations=recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendations error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get recommendations")

