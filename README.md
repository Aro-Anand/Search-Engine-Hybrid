# Semantic Search Engine

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**Fast, intelligent search for small-scale datasets using hybrid keyword + semantic matching.**

## 🌟 Features

- ⚡ **Sub-100ms Search Latency** - Optimized for real-time user experience
- 🧠 **Semantic Understanding** - Finds relevant results even with different wording
- 🔍 **Google-like Autocomplete** - Intelligent suggestions as users type
- 📊 **Hybrid Ranking** - Combines keyword matching with semantic similarity
- 🚀 **Production-Ready** - Comprehensive logging, monitoring, and error handling
- 📱 **RESTful API** - Easy integration with any frontend framework
- 🎯 **Optimized for 200-10K Listings** - Perfect for small to medium catalogs

## 🏗️ Architecture

```
┌──────────────┐
│   Frontend   │
│ (React/Vue)  │
└──────┬───────┘
       │ REST API
       ▼
┌──────────────────────────────────┐
│     FastAPI Server (Python)      │
│  ┌────────────────────────────┐  │
│  │  Hybrid Search Engine      │  │
│  │  • Keyword Filter          │  │
│  │  • Semantic Re-ranking     │  │
│  │  • Autocomplete            │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ Embeddings   │
│ (in-memory)  │
└──────────────┘
```

### How It Works

1. **Indexing Phase** (one-time at startup):
   - Load listings from JSON/database
   - Generate embeddings using sentence-transformers
   - Build autocomplete index (Trie structure)

2. **Search Pipeline** (per query):
   - **Stage 1**: Fast keyword filtering (reduces candidates)
   - **Stage 2**: Semantic re-ranking (AI-powered relevance)
   - **Stage 3**: Score fusion (combines keyword + semantic scores)

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/semantic-search-engine.git
cd semantic-search-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
# Start API server
python -m app.main

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Usage Examples

```bash
# Search for listings
curl "http://localhost:8000/api/v1/search?q=laptop&limit=5"

# Get autocomplete suggestions
curl "http://localhost:8000/api/v1/autocomplete?q=lap&limit=5"

# Add recent search
curl -X POST "http://localhost:8000/api/v1/recent?user_id=user123&query=gaming laptop"

# Get recent searches
curl "http://localhost:8000/api/v1/recent/user123"

# Health check
curl "http://localhost:8000/health"
```

## 📊 API Documentation

### Search Endpoint

```http
GET /api/v1/search?q={query}&limit={limit}&offset={offset}
```

**Parameters:**
- `q` (required): Search query string
- `limit` (optional): Max results, default 10, max 100
- `offset` (optional): Pagination offset, default 0

**Response:**
```json
{
  "query": "laptop",
  "total_results": 42,
  "results": [
    {
      "id": "123",
      "title": "Gaming Laptop",
      "description": "High-performance laptop...",
      "score": 0.87,
      "keyword_score": 0.9,
      "semantic_score": 0.85,
      "match_type": "hybrid"
    }
  ],
  "processing_time_ms": 45
}
```

### Autocomplete Endpoint

```http
GET /api/v1/autocomplete?q={partial}&limit={limit}
```

**Response:**
```json
{
  "query": "lap",
  "suggestions": ["laptop", "laptop bag", "laptop stand"]
}
```

[Full API documentation](docs/API.md) | [Interactive Docs](http://localhost:8000/docs)

## 🧪 Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_search_engine.py -v

# Load testing
locust -f tests/locustfile.py --host http://localhost:8000
```

## 📦 Project Structure

```
semantic-search-engine/
├── app/
│   ├── core/
│   │   ├── search_engine.py      # Hybrid search logic
│   │   ├── autocomplete.py       # Trie-based autocomplete
│   │   └── __init__.py
│   ├── main.py                   # FastAPI application
│   └── __init__.py
├── data/
│   └── listings.json             # Sample data
├── tests/
│   ├── test_search_engine.py
│   ├── test_autocomplete.py
│   └── test_api.py
├── docs/
│   ├── API.md                    # API documentation
│   ├── DEPLOYMENT.md             # Deployment guide
│   └── ARCHITECTURE.md           # System architecture
├── deployment/
│   ├── systemd/
│   │   └── semantic-search.service
│   └── nginx/
│       └── semantic-search.conf
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── README.md                     # This file
└── LICENSE                       # MIT License
```

## 🚢 Deployment

### AWS EC2 Deployment

**Recommended Instance:** `t3.medium` (2 vCPU, 4 GB RAM) - ~$30/month

See detailed [Deployment Guide](docs/DEPLOYMENT.md) for step-by-step instructions.

**Quick Deploy:**

```bash
# On EC2 instance
git clone <repo-url>
cd semantic-search-engine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up systemd service
sudo cp deployment/systemd/semantic-search.service /etc/systemd/system/
sudo systemctl enable semantic-search
sudo systemctl start semantic-search

# Configure nginx
sudo cp deployment/nginx/semantic-search.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/semantic-search /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### Docker Deployment

```bash
# Build image
docker build -t semantic-search .

# Run container
docker run -p 8000:8000 -v $(pwd)/data:/app/data semantic-search
```

## ⚙️ Configuration

Create a `.env` file:

```env
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=2

# Model Settings
MODEL_NAME=all-MiniLM-L6-v2

# CORS
ALLOWED_ORIGINS=https://yourwebsite.com

# Logging
LOG_LEVEL=INFO
```

## 📈 Performance

**Benchmarks** (t3.medium instance, 200 listings):

| Operation | p50 | p95 | p99 |
|-----------|-----|-----|-----|
| Search | 45ms | 80ms | 150ms |
| Autocomplete | 15ms | 30ms | 50ms |
| Health Check | 2ms | 5ms | 10ms |

**Throughput:**
- Search: 100+ req/sec
- Autocomplete: 200+ req/sec
- Concurrent users: 50+

## 🛠️ Tech Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI 0.109
- **ML Model**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector Ops**: NumPy, scikit-learn
- **Server**: Uvicorn (ASGI)
- **Testing**: pytest, httpx, locust

## 📚 Documentation

- [API Reference](docs/API.md) - Complete API documentation
- [Architecture Overview](docs/ARCHITECTURE.md) - System design and decisions
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment steps
- [Contributing Guidelines](docs/CONTRIBUTING.md) - How to contribute
- [Product Requirements](PRD.md) - Detailed PRD

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](docs/CONTRIBUTING.md) first.

```bash
# Fork repository
# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and test
pytest --cov=app

# Format code
black app/ tests/
flake8 app/ tests/

# Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

# Create Pull Request
```