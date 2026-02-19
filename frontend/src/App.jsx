import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Filter, PlusCircle, Book, FileText, Briefcase } from 'lucide-react';
import './App.css';

const API_BASE = 'http://localhost:9999/api/v1';

function App() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [postType, setPostType] = useState('');
    const [loading, setLoading] = useState(false);
    const [stats, setStats] = useState(null);
    const [debounceTimer, setDebounceTimer] = useState(null);

    // Fetch stats on load
    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const res = await axios.get(`${API_BASE}/health`.replace('/api/v1', ''));
            setStats(res.data);
        } catch (err) {
            console.error('Failed to fetch stats');
        }
    };

    const handleQueryChange = (e) => {
        const value = e.target.value;
        setQuery(value);

        if (debounceTimer) clearTimeout(debounceTimer);

        if (value.length < 3) {
            setSuggestions([]);
            setShowSuggestions(false);
            return;
        }

        const timer = setTimeout(async () => {
            try {
                const res = await axios.get(`${API_BASE}/autocomplete?q=${encodeURIComponent(value)}&limit=6`);
                setSuggestions(res.data.suggestions || []);
                setShowSuggestions(true);
            } catch (err) {
                console.error('Autocomplete error');
            }
        }, 200);

        setDebounceTimer(timer);
    };

    const selectSuggestion = (s) => {
        setQuery(s);
        setShowSuggestions(false);
        handleSearch(null, s);
    };

    const handleSearch = async (e, forcedQuery = null) => {
        if (e) e.preventDefault();
        const finalQuery = forcedQuery || query;
        setLoading(true);
        setShowSuggestions(false);
        try {
            let url = `${API_BASE}/search?q=${encodeURIComponent(finalQuery || 'franchise')}`;
            if (postType) url += `&post_type=${postType}`;

            const res = await axios.get(url);
            setResults(res.data.results);
        } catch (err) {
            alert('Search failed. Is the API running?');
        } finally {
            setLoading(false);
        }
    };

    const getTagClass = (type) => {
        switch (type) {
            case 'blog': return 'tag tag-blog';
            case 'page': return 'tag tag-page';
            default: return 'tag tag-listing';
        }
    };

    const getIcon = (type) => {
        switch (type) {
            case 'blog': return <Book size={14} />;
            case 'page': return <FileText size={14} />;
            default: return <Briefcase size={14} />;
        }
    };

    return (
        <div className="container">
            <header>
                <h1>Franchise Discovery Demo</h1>
                <p>Testing Multi-Sector Semantic Search Integration</p>
                {stats && (
                    <div style={{ marginTop: '1rem', fontSize: '0.8rem', color: '#666' }}>
                        Index Status: <b>{stats.indexed_listings}</b> items online
                    </div>
                )}
            </header>

            <form className="search-section" onSubmit={handleSearch}>
                <div style={{ position: 'relative', flex: 1, display: 'flex', alignItems: 'center' }}>
                    <Search style={{ position: 'absolute', left: '12px', color: '#94a3b8' }} size={20} />
                    <input
                        style={{ paddingLeft: '40px' }}
                        type="text"
                        placeholder="Search blogs, pages, or franchises..."
                        value={query}
                        onChange={handleQueryChange}
                        onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                    />
                    {showSuggestions && suggestions.length > 0 && (
                        <div className="suggestions-dropdown">
                            {suggestions.map((s, i) => (
                                <div key={i} className="suggestion-item" onClick={() => selectSuggestion(s)}>
                                    {s}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <select value={postType} onChange={(e) => setPostType(e.target.value)}>
                    <option value="">All Types</option>
                    <option value="listing">Franchises</option>
                    <option value="blog">Blogs</option>
                    <option value="page">Pages</option>
                </select>

                <button type="submit" disabled={loading}>
                    {loading ? 'Searching...' : 'Search'}
                </button>
            </form>

            <div className="grid">
                {results.length > 0 ? (
                    results.map((item) => (
                        <div
                            key={item.id}
                            className="card"
                            style={{ cursor: 'pointer' }}
                            onClick={() => window.open(`${API_BASE}/recommend/${item.slug || item.id}`, '_blank')}
                        >
                            <div className={getTagClass(item.post_type)}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    {getIcon(item.post_type)} {item.sector}
                                </span>
                            </div>
                            <h3 className="card-title">{item.title}</h3>
                            <p className="card-desc">{item.description}</p>
                            <div className="card-footer">
                                <span>{item.location || 'N/A'}</span>
                                <span style={{ color: '#16a34a', fontWeight: 'bold' }}>
                                    {Math.round(item.score * 100)}% Match
                                </span>
                            </div>
                            <div style={{ marginTop: '0.5rem', fontSize: '0.7rem', color: '#94a3b8' }}>
                                Slug: {item.slug}
                            </div>
                        </div>
                    ))
                ) : (
                    <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                        {loading ? 'Thinking...' : 'Start searching to see AI-powered matches'}
                    </div>
                )}
            </div>

            <div style={{ marginTop: '4rem', padding: '2rem', background: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                <h2 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <PlusCircle color="#2563eb" /> Integration Quick-Test (POST)
                </h2>
                <p style={{ fontSize: '0.9rem', color: '#64748b', marginBottom: '1.5rem' }}>
                    Try adding a new blog or listing via the developer console or Postman using the payloads from <code>walkthrough.md</code>, then search for it here to see it appear instantly!
                </p>
                <div style={{ display: 'flex', gap: '1rem', opacity: 0.7 }}>
                    <code style={{ background: '#f1f5f9', padding: '1rem', borderRadius: '8px', flex: 1, fontSize: '0.8rem' }}>
                        POST /api/v1/blogs<br />
                        {JSON.stringify({ id: Date.now(), title: "React Test", slug: "react-test" }, null, 2)}
                    </code>
                </div>
            </div>
        </div>
    );
}

export default App;
