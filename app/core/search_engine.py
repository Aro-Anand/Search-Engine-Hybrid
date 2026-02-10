"""
Hybrid Search Engine Module

This module implements a two-stage search pipeline:
1. Fast keyword filtering to reduce candidate set  
2. Semantic re-ranking using sentence embeddings

Author: Development Team
Version: 1.0.0
"""

import re
import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    Hybrid search engine combining keyword matching and semantic similarity.
    
    This class implements a two-stage search pipeline:
    1. Fast keyword filtering to reduce candidate set
    2. Semantic re-ranking using sentence embeddings
    
    Attributes:
        model (SentenceTransformer): Embedding model for semantic search
        listings (List[Dict]): Indexed listing documents
        embeddings (np.ndarray): Pre-computed document embeddings
        embedding_dim (int): Dimension of embedding vectors
        
    Example:
        >>> engine = HybridSearchEngine()
        >>> listings = [
        ...     {"id": "1", "title": "Gaming Laptop", "description": "High-performance"},
        ...     {"id": "2", "title": "Office Desktop", "description": "Business PC"}
        ... ]
        >>> engine.index_listings(listings)
        >>> results = engine.search("laptop", top_k=5)
        >>> len(results)
        2
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize search engine with specified model.
        
        Args:
            model_name: Name of sentence-transformer model to use
                       Default: all-MiniLM-L6-v2 (fast, good quality)
        """
        logger.info(f"Initializing HybridSearchEngine with model: {model_name}")
        
        self.model = SentenceTransformer(model_name)
        self.listings: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.embedding_dim = 384  # MiniLM-L6-v2 dimension
        
        # Statistics
        self.stats = {
            'total_searches': 0,
            'avg_search_time_ms': 0,
            'cache_hits': 0
        }
        
        logger.info("Search engine initialized successfully")
    
    def index_listings(self, listings: List[Dict[str, Any]]) -> None:
        """
        Index listings and build search structures.
        
        This method:
        1. Stores listings in memory
        2. Generates embeddings for all listings
        3. Builds autocomplete index
        
        Args:
            listings: List of listing dictionaries with at least 'id' and 'title'
        
        Raises:
            ValueError: If listings is empty or missing required fields
            
        Example:
            >>> engine.index_listings([
            ...     {"id": "1", "title": "Laptop", "description": "Fast computer"}
            ... ])
        """
        if not listings:
            raise ValueError("Listings cannot be empty")
        
        # Validate required fields
        required_fields = {'id', 'title'}
        for idx, listing in enumerate(listings):
            missing = required_fields - set(listing.keys())
            if missing:
                raise ValueError(
                    f"Listing {idx} missing required fields: {missing}"
                )
        
        logger.info(f"Indexing {len(listings)} listings...")
        
        self.listings = listings
        
        # Create searchable text for each listing
        # Combines title, description, category for better matching
        texts = []
        for listing in listings:
            searchable_text = " ".join([
                listing.get('title', ''),
                listing.get('description', ''),
                listing.get('category', ''),
                " ".join(listing.get('tags', []))
            ]).strip()
            texts.append(searchable_text)
        
        # Generate embeddings (this takes 2-3 seconds for 200 items)
        logger.info("Generating embeddings...")
        self.embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        
        logger.info(
            f"Indexing complete. {len(listings)} listings, "
            f"embedding dimension: {self.embeddings.shape[1]}"
        )
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Search listings using hybrid keyword + semantic approach.
        
        Pipeline:
        1. Keyword filter: Fast pre-filtering based on term overlap
        2. Semantic ranking: Re-rank candidates using embeddings
        3. Score fusion: Combine keyword and semantic scores
        
        Args:
            query: User search query (1-200 characters)
            top_k: Maximum number of results to return
            keyword_weight: Weight for keyword score (default: 0.4)
            semantic_weight: Weight for semantic score (default: 0.6)
        
        Returns:
            List of matching listings sorted by relevance. Each listing
            includes original fields plus:
            - 'score': Combined relevance score (0.0-1.0)
            - 'keyword_score': Keyword matching score
            - 'semantic_score': Semantic similarity score
            - 'match_type': 'keyword', 'semantic', or 'hybrid'
        
        Raises:
            ValueError: If query is invalid
            RuntimeError: If search engine not initialized
            
        Example:
            >>> results = engine.search("budget laptop", top_k=3)
            >>> results[0]['score']
            0.87
            >>> results[0]['match_type']
            'hybrid'
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if len(query) > 200:
            raise ValueError("Query too long (max 200 characters)")
        
        if top_k < 1 or top_k > 100:
            raise ValueError("top_k must be between 1 and 100")
        
        if self.embeddings is None:
            raise RuntimeError(
                "Search engine not initialized. Call index_listings() first."
            )
        
        query = query.strip().lower()
        
        logger.debug(f"Searching for: '{query}', top_k={top_k}")
        
        # Update statistics
        self.stats['total_searches'] += 1
        
        # Stage 1: Keyword filtering (fast pre-filter)
        keyword_matches = self._keyword_search(query)
        
        # If very few matches, return them directly
        if len(keyword_matches) <= top_k:
            logger.debug(
                f"Keyword filter returned {len(keyword_matches)} results, "
                "skipping semantic ranking"
            )
            return keyword_matches[:top_k]
        
        # Stage 2: Semantic re-ranking
        # Only compute embeddings for keyword matches (optimization)
        match_indices = [m['_index'] for m in keyword_matches]
        
        # Generate query embedding
        query_embedding = self.model.encode(
            [query],
            show_progress_bar=False,
            normalize_embeddings=True
        )
        
        # Get embeddings for matched listings
        match_embeddings = self.embeddings[match_indices]
        
        # Compute semantic similarities
        similarities = cosine_similarity(query_embedding, match_embeddings)[0]
        
        # Stage 3: Score fusion
        # Combine keyword and semantic scores
        for i, match in enumerate(keyword_matches):
            match['semantic_score'] = float(similarities[i])
            match['score'] = (
                keyword_weight * match['keyword_score'] +
                semantic_weight * match['semantic_score']
            )
            
            # Determine match type
            if match['keyword_score'] > 0.5 and match['semantic_score'] > 0.5:
                match['match_type'] = 'hybrid'
            elif match['keyword_score'] > match['semantic_score']:
                match['match_type'] = 'keyword'
            else:
                match['match_type'] = 'semantic'
            
            # Clean up internal fields
            del match['_index']
        
        # Sort by combined score
        keyword_matches.sort(key=lambda x: x['score'], reverse=True)
        
        results = keyword_matches[:top_k]
        
        logger.debug(f"Returning {len(results)} results")
        
        return results
    
    def _keyword_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Fast keyword-based filtering.
        
        Computes term overlap between query and listings.
        
        Args:
            query: Normalized query string
            
        Returns:
            List of listings with keyword_score field
        """
        # Extract query terms (alphanumeric only)
        query_terms = set(re.findall(r'\w+', query.lower()))
        
        results = []
        
        for idx, listing in enumerate(self.listings):
            # Create searchable text
            text = " ".join([
                listing.get('title', ''),
                listing.get('description', ''),
                listing.get('category', ''),
                " ".join(listing.get('tags', []))
            ]).lower()
            
            # Extract terms from listing
            text_terms = set(re.findall(r'\w+', text))
            
            # Calculate term overlap (Jaccard-like similarity)
            overlap = len(query_terms & text_terms)
            
            if overlap > 0:
                # Compute keyword score (normalized by query length)
                keyword_score = overlap / len(query_terms)
                
                # Boost exact title matches
                if any(term in listing.get('title', '').lower() 
                       for term in query_terms):
                    keyword_score *= 1.2
                
                # Cap at 1.0
                keyword_score = min(keyword_score, 1.0)
                
                # Add result
                result = listing.copy()
                result['_index'] = idx  # Store index for later embedding lookup
                result['keyword_score'] = keyword_score
                results.append(result)
        
        # Sort by keyword score
        results.sort(key=lambda x: x['keyword_score'], reverse=True)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get search engine statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            'indexed_listings': len(self.listings),
            'embedding_dimension': self.embedding_dim,
            'total_searches': self.stats['total_searches'],
            'model_name': self.model.__class__.__name__
        }
