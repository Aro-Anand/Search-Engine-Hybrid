"""
Custom exceptions for the application.

This module defines custom exception classes used throughout the application.
"""

from fastapi import HTTPException, status


class SearchEngineNotInitializedError(Exception):
    """Raised when search engine is not initialized."""
    pass


class InvalidQueryError(Exception):
    """Raised when search query is invalid."""
    pass


class ListingNotFoundError(HTTPException):
    """Raised when a listing is not found."""
    
    def __init__(self, listing_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with id '{listing_id}' not found"
        )


class DataFileError(Exception):
    """Raised when there's an error with the data file."""
    pass
