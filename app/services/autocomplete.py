"""
Autocomplete Engine Module

Provides fast autocomplete suggestions using Trie (prefix tree) data structure.

Author: Development Team
Version: 1.0.0
"""

import re
import logging
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class TrieNode:
    """
    Node in a Trie data structure.
    
    Attributes:
        children: Dictionary mapping characters to child nodes
        is_end: True if this node marks the end of a word
        frequency: How often this term has been searched
    """
    
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end: bool = False
        self.frequency: int = 0


class AutocompleteEngine:
    """
    Fast autocomplete engine using Trie data structure.
    
    Provides prefix-based suggestions with frequency ranking.
    Supports building index from listings and tracking popular searches.
    
    Example:
        >>> autocomplete = AutocompleteEngine()
        >>> autocomplete.insert("laptop", frequency=100)
        >>> autocomplete.insert("laptop bag", frequency=50)
        >>> autocomplete.suggest("lap")
        ['laptop', 'laptop bag']
    """
    
    def __init__(self, max_suggestions: int = 10):
        """
        Initialize autocomplete engine.
        
        Args:
            max_suggestions: Maximum number of suggestions to return
        """
        self.root = TrieNode()
        self.max_suggestions = max_suggestions
        self.total_terms = 0
        
        logger.info("AutocompleteEngine initialized")
    
    def build_from_listings(self, listings: List[Dict]) -> None:
        """
        Build autocomplete index from franchise data.
        
        Focuses on Titles, Sectors, and Tags to keep suggestions relevant.
        """
        logger.info(f"Building autocomplete index from {len(listings)} franchise listings...")
        
        term_frequencies = defaultdict(int)
        
        # Common stop words to exclude from suggestions
        stop_words = {
            'what', 'are', 'the', 'you', 'how', 'they', 'this', 'that', 'with', 'from',
            'business', 'franchise', 'opportunity', 'available', 'good', 'your', 'about'
        }
        
        for listing in listings:
            # 1. Primary terms: Titles are most important
            title = listing.get('title', '').lower()
            if title:
                term_frequencies[title] += 10 # High weight for exact titles
                
                # Split title into individual words
                title_words = re.findall(r'\b[a-z]{3,}\b', title)
                for word in title_words:
                    if word not in stop_words:
                        term_frequencies[word] += 5
            
            # 2. Category/Sector terms
            sector = listing.get('sector', '').lower()
            if sector:
                term_frequencies[sector] += 8
                
            # 3. Tags
            for tag in listing.get('tags', []):
                tag = tag.lower()
                if tag:
                    term_frequencies[tag] += 5
        
        # Insert terms into trie
        for term, freq in term_frequencies.items():
            # Only index terms that have some minimum weight/frequency
            if len(term) >= 3:
                self.insert(term, frequency=freq)
        
        logger.info(
            f"Franchise autocomplete index built with {self.total_terms} relevant terms"
        )
    
    def insert(self, term: str, frequency: int = 1) -> None:
        """
        Insert a term into the autocomplete index.
        
        Args:
            term: Term to index (will be lowercased)
            frequency: How often this term appears/is searched
            
        Example:
            >>> autocomplete.insert("laptop", frequency=100)
            >>> autocomplete.insert("laptop bag", frequency=50)
        """
        term = term.lower().strip()
        
        if not term:
            return
        
        node = self.root
        
        # Traverse/create path for each character
        for char in term:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        
        # Mark end of term
        if not node.is_end:
            self.total_terms += 1
            
        node.is_end = True
        node.frequency = max(node.frequency, frequency)
    
    def add_term(self, term: str, frequency: int = 1) -> None:
        """
        Add a term to the autocomplete index.
        
        Alias for insert() method for better API clarity.
        
        Args:
            term: Term to add (will be lowercased)
            frequency: How often this term appears/is searched
        """
        self.insert(term, frequency)
    
    def suggest(self, prefix: str, limit: Optional[int] = None) -> List[str]:
        """
        Get autocomplete suggestions for a prefix.
        
        Args:
            prefix: Partial query string
            limit: Maximum suggestions to return (default: self.max_suggestions)
            
        Returns:
            List of suggested terms, sorted by frequency
            
        Example:
            >>> autocomplete.suggest("lap", limit=5)
            ['laptop', 'laptop bag', 'laptop stand']
        """
        if limit is None:
            limit = self.max_suggestions
        
        prefix = prefix.lower().strip()
        
        if not prefix:
            return []
        
        # Navigate to prefix node
        node = self.root
        for char in prefix:
            if char not in node.children:
                # Prefix not found
                return []
            node = node.children[char]
        
        # Collect all completions from this point
        suggestions = []
        self._collect_words(node, prefix, suggestions, limit * 3)  # Get extra for sorting
        
        # Sort by frequency (descending)
        suggestions.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the terms (not frequencies)
        return [term for term, _ in suggestions[:limit]]
    
    def _collect_words(
        self,
        node: TrieNode,
        current_word: str,
        suggestions: List[tuple],
        limit: int
    ) -> None:
        """
        Recursively collect all words from a node.
        
        Args:
            node: Current trie node
            current_word: Word built so far
            suggestions: List to append (word, frequency) tuples
            limit: Stop when this many suggestions collected
        """
        if len(suggestions) >= limit:
            return
        
        # If this is end of a word, add it
        if node.is_end:
            suggestions.append((current_word, node.frequency))
        
        # Recurse through children (alphabetically)
        for char in sorted(node.children.keys()):
            self._collect_words(
                node.children[char],
                current_word + char,
                suggestions,
                limit
            )
    
    def record_search(self, query: str) -> None:
        """
        Record a search query to boost its frequency.
        
        This helps surface popular searches in suggestions.
        
        Args:
            query: Search query that was executed
        """
        query = query.lower().strip()
        
        if not query or len(query) < 2:
            return
        
        # Update frequency if term exists, otherwise insert
        node = self.root
        exists = True
        
        for char in query:
            if char not in node.children:
                exists = False
                break
            node = node.children[char]
        
        if exists and node.is_end:
            # Increment existing term frequency
            node.frequency += 1
        else:
            # Insert new term with frequency 1
            self.insert(query, frequency=1)
    
    def get_popular_terms(self, limit: int = 10) -> List[tuple]:
        """
        Get most popular search terms.
        
        Args:
            limit: How many terms to return
            
        Returns:
            List of (term, frequency) tuples
        """
        all_terms = []
        self._collect_all_terms(self.root, "", all_terms)
        
        # Sort by frequency
        all_terms.sort(key=lambda x: x[1], reverse=True)
        
        return all_terms[:limit]
    
    def _collect_all_terms(
        self,
        node: TrieNode,
        current_word: str,
        terms: List[tuple]
    ) -> None:
        """Recursively collect all terms with frequencies."""
        if node.is_end:
            terms.append((current_word, node.frequency))
        
        for char, child in node.children.items():
            self._collect_all_terms(child, current_word + char, terms)
