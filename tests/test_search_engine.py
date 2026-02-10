"""
Test suite for Hybrid Search Engine

Tests keyword filtering, semantic ranking, and hybrid scoring.
"""

import pytest
from app.core.search_engine import HybridSearchEngine


@pytest.fixture
def sample_listings():
    """Fixture providing sample listing data."""
    return [
        {
            "id": "1",
            "title": "Gaming Laptop - High Performance",
            "description": "Powerful laptop for gaming and creative work",
            "category": "Electronics",
            "price": 1299.99,
            "tags": ["laptop", "gaming", "computer"]
        },
        {
            "id": "2",
            "title": "Budget Notebook Computer",
            "description": "Affordable laptop for everyday tasks",
            "category": "Electronics",
            "price": 499.99,
            "tags": ["laptop", "budget", "notebook"]
        },
        {
            "id": "3",
            "title": "Wireless Mouse - Ergonomic",
            "description": "Comfortable wireless mouse for office use",
            "category": "Electronics",
            "price": 29.99,
            "tags": ["mouse", "wireless", "accessory"]
        },
        {
            "id": "4",
            "title": "Mechanical Keyboard RGB",
            "description": "Premium mechanical keyboard with RGB lighting",
            "category": "Electronics",
            "price": 149.99,
            "tags": ["keyboard", "mechanical", "gaming"]
        },
        {
            "id": "5",
            "title": "Office Desktop Computer",
            "description": "Business workstation for productivity",
            "category": "Electronics",
            "price": 899.99,
            "tags": ["desktop", "computer", "office"]
        }
    ]


@pytest.fixture
def search_engine(sample_listings):
    """Fixture providing initialized search engine."""
    engine = HybridSearchEngine()
    engine.index_listings(sample_listings)
    return engine


class TestHybridSearchEngine:
    """Test suite for HybridSearchEngine class."""
    
    def test_initialization(self):
        """Test that engine initializes correctly."""
        engine = HybridSearchEngine()
        assert engine.model is not None
        assert engine.embeddings is None
        assert len(engine.listings) == 0
    
    def test_index_listings(self, sample_listings):
        """Test listing indexing."""
        engine = HybridSearchEngine()
        engine.index_listings(sample_listings)
        
        assert len(engine.listings) == len(sample_listings)
        assert engine.embeddings is not None
        assert engine.embeddings.shape[0] == len(sample_listings)
    
    def test_index_empty_listings_raises_error(self):
        """Test that empty listings raise ValueError."""
        engine = HybridSearchEngine()
        
        with pytest.raises(ValueError, match="empty"):
            engine.index_listings([])
    
    def test_index_missing_required_fields(self):
        """Test that listings without required fields raise error."""
        engine = HybridSearchEngine()
        invalid_listings = [{"description": "Missing id and title"}]
        
        with pytest.raises(ValueError, match="required fields"):
            engine.index_listings(invalid_listings)
    
    def test_search_returns_results(self, search_engine):
        """Test that search returns results for valid query."""
        results = search_engine.search("laptop", top_k=5)
        
        assert len(results) > 0
        assert all('score' in r for r in results)
        assert all('id' in r for r in results)
    
    def test_search_respects_top_k(self, search_engine):
        """Test that search returns at most top_k results."""
        results = search_engine.search("computer", top_k=2)
        assert len(results) <= 2
    
    def test_search_empty_query_raises_error(self, search_engine):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            search_engine.search("")
    
    def test_search_long_query_raises_error(self, search_engine):
        """Test that overly long query raises ValueError."""
        long_query = "x" * 201
        
        with pytest.raises(ValueError, match="too long"):
            search_engine.search(long_query)
    
    def test_search_invalid_top_k(self, search_engine):
        """Test that invalid top_k raises ValueError."""
        with pytest.raises(ValueError, match="between 1 and 100"):
            search_engine.search("laptop", top_k=0)
        
        with pytest.raises(ValueError, match="between 1 and 100"):
            search_engine.search("laptop", top_k=101)
    
    def test_search_before_indexing_raises_error(self):
        """Test that search before indexing raises RuntimeError."""
        engine = HybridSearchEngine()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            engine.search("laptop")
    
    def test_semantic_similarity(self, search_engine):
        """Test that semantically similar terms match."""
        # "notebook" should match "laptop" semantically
        results = search_engine.search("notebook", top_k=5)
        
        # Should find the "Budget Notebook Computer" and "Gaming Laptop"
        titles = [r['title'].lower() for r in results]
        assert any('notebook' in title or 'laptop' in title for title in titles)
    
    def test_keyword_matching(self, search_engine):
        """Test exact keyword matching."""
        results = search_engine.search("gaming", top_k=5)
        
        # Should prioritize exact matches
        assert len(results) > 0
        first_result_title = results[0]['title'].lower()
        assert 'gaming' in first_result_title
    
    def test_hybrid_scoring(self, search_engine):
        """Test that hybrid scoring combines keyword and semantic scores."""
        results = search_engine.search("laptop", top_k=3)
        
        # All results should have scoring information
        for result in results:
            assert 'keyword_score' in result
            assert 'semantic_score' in result
            assert 'score' in result
            assert 'match_type' in result
            
            # Scores should be between 0 and 1
            assert 0 <= result['keyword_score'] <= 1
            assert 0 <= result['semantic_score'] <= 1
            assert 0 <= result['score'] <= 1
    
    def test_match_types(self, search_engine):
        """Test that match_type is correctly assigned."""
        results = search_engine.search("computer laptop", top_k=5)
        
        # Should have various match types
        match_types = set(r['match_type'] for r in results)
        assert match_types.issubset({'keyword', 'semantic', 'hybrid'})
    
    def test_get_stats(self, search_engine):
        """Test statistics retrieval."""
        stats = search_engine.get_stats()
        
        assert 'indexed_listings' in stats
        assert 'embedding_dimension' in stats
        assert 'total_searches' in stats
        assert stats['indexed_listings'] == 5
    
    def test_search_updates_stats(self, search_engine):
        """Test that search calls update statistics."""
        initial_stats = search_engine.get_stats()
        initial_count = initial_stats['total_searches']
        
        search_engine.search("laptop", top_k=5)
        
        updated_stats = search_engine.get_stats()
        assert updated_stats['total_searches'] == initial_count + 1


class TestKeywordSearch:
    """Test keyword search functionality."""
    
    def test_keyword_filter(self, search_engine):
        """Test keyword filtering."""
        results = search_engine._keyword_search("gaming")
        
        assert len(results) > 0
        assert all('keyword_score' in r for r in results)
    
    def test_multi_term_query(self, search_engine):
        """Test query with multiple terms."""
        results = search_engine._keyword_search("gaming laptop")
        
        # Should find items with both or either term
        assert len(results) > 0
    
    def test_case_insensitive(self, search_engine):
        """Test that search is case-insensitive."""
        results_lower = search_engine._keyword_search("laptop")
        results_upper = search_engine._keyword_search("LAPTOP")
        results_mixed = search_engine._keyword_search("LapTop")
        
        # All should return same results
        assert len(results_lower) == len(results_upper) == len(results_mixed)
