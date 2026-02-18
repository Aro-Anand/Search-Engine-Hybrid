"""
Pydantic schemas for request/response validation.

This module defines all data models used in the API endpoints.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class ListingCreate(BaseModel):
    """Schema for creating a new franchise listing."""
    
    id: Union[str, int] = Field(..., description="Unique franchise listing identifier")
    title: str = Field(..., min_length=1, max_length=200, description="Franchise name/title")
    description: Optional[str] = Field(None, description="Franchise description and details")
    sector: Optional[str] = Field(None, description="Business sector (e.g., Food & Beverage, Retail, Technology)")
    location: Optional[str] = Field(None, description="Franchise location or availability")
    investment_range: Optional[str] = Field(None, description="Investment range (e.g., ₹10L-₹20L)")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization")
    slug: str = Field(..., description="URL-friendly slug provided by UI")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "franchise_001",
                "title": "Pizza Hut Franchise",
                "description": "Leading pizza chain franchise opportunity",
                "sector": "Food & Beverage",
                "location": "Pan India",
                "investment_range": "₹50L-₹1Cr",
                "tags": ["pizza", "food", "restaurant"]
            }
        }
    )


class ListingResponse(BaseModel):
    """Schema for franchise listing response."""
    
    id: Union[str, int]  # Accept both string and integer IDs
    title: str
    description: Optional[str] = None
    sector: Optional[str] = None
    location: Optional[str] = None
    investment_range: Optional[str] = None
    tags: Optional[List[str]] = None
    slug: Optional[str] = Field(None, description="URL-friendly slug")
    score: Optional[float] = Field(None, description="Relevance score (0.0-1.0)")
    keyword_score: Optional[float] = Field(None, description="Keyword matching score")
    semantic_score: Optional[float] = Field(None, description="Semantic similarity score")
    match_type: Optional[str] = Field(None, description="Match type: keyword, semantic, or hybrid")
    
    model_config = ConfigDict(from_attributes=True)


class SearchQuery(BaseModel):
    """Schema for search query parameters."""
    
    q: str = Field(..., min_length=1, max_length=200, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "q": "office space downtown",
                "limit": 10,
                "offset": 0
            }
        }
    )


class SearchResponse(BaseModel):
    """Schema for search response."""
    
    query: str = Field(..., description="The search query")
    total_results: int = Field(..., description="Total matching results")
    results: List[ListingResponse] = Field(..., description="List of matching listings")
    processing_time_ms: float = Field(..., description="Search latency in milliseconds")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "office space",
                "total_results": 15,
                "results": [],
                "processing_time_ms": 45.23
            }
        }
    )


class AutocompleteResponse(BaseModel):
    """Schema for autocomplete response."""
    
    query: str = Field(..., description="Partial query string")
    suggestions: List[str] = Field(..., description="List of suggested terms")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "off",
                "suggestions": ["office", "office space", "office downtown"]
            }
        }
    )


class RetrainResponse(BaseModel):
    """Schema for retrain response."""
    
    status: str = Field(..., description="Status of the retrain operation")
    message: str = Field(..., description="Detailed message")
    listings_count: int = Field(..., description="Number of listings indexed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Search engine retrained successfully",
                "listings_count": 150
            }
        }
    )


class FiltersResponse(BaseModel):
    """Schema for available filters response."""
    
    sectors: List[str] = Field(..., description="Available business sectors")
    locations: List[str] = Field(..., description="Available locations")
    investment_ranges: List[str] = Field(..., description="Available investment ranges")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sectors": ["Food & Beverage", "Retail", "Technology", "Health & Fitness"],
                "locations": ["Pan India", "Delhi NCR", "Mumbai", "Bangalore"],
                "investment_ranges": ["₹5L-₹10L", "₹10L-₹20L", "₹20L-₹50L", "₹50L-₹1Cr"]
            }
        }
    )


class RecommendationResponse(BaseModel):
    """Schema for franchise recommendations response."""
    
    franchise_id: Union[str, int] = Field(..., description="ID of the source franchise")
    franchise_title: str = Field(..., description="Title of the source franchise")
    recommendations: List[ListingResponse] = Field(..., description="List of similar franchises")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "franchise_id": "123",
                "franchise_title": "Pizza Hut Franchise",
                "recommendations": []
            }
        }
    )

