# OSINT Aggregator

Multi-source OSINT (Open Source Intelligence) data aggregation and analysis platform with AI-powered event classification using local LLM processing.

![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Next.js](https://img.shields.io/badge/Next.js-16-black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![PostGIS](https://img.shields.io/badge/PostGIS-3.4-orange)

## Features

### 🔍 Data Collection
- **Telegram**: Collect from channels using your personal account (Telethon)
- **RSS Feeds**: Aggregate from any RSS/Atom feed
- **Discord**: Bot-based collection (optional)
- **FlightRadar24**: Track aircraft positions (optional)
- **MarineTraffic**: Monitor vessels (optional)

### 🤖 AI Processing
- **Local LLM**: LM Studio integration for on-premise AI
- **Auto Classification**: Category & threat level extraction
- **Geocoding**: Automatic location mapping
- **Deduplication**: Content-based hashing

### 🗺️ Visualization
- **Interactive Map**: Mapbox-powered global view
- **Real-time Feed**: Filterable event stream
- **Statistics**: Category, threat, geographic breakdowns
- **WebSocket**: Live updates

## Quick Start

### Prerequisites

1. **Docker & Docker Compose**
2. **LM Studio** - [lmstudio.ai](https://lmstudio.ai)
   - Download & install
   - Load a model (e.g., Qwen 2.5 7B)
   - Start local server (port 1234)
3. **Mapbox Token** - [mapbox.com](https://account.mapbox.com)
4. **Telegram API** (optional) - [my.telegram.org/apps](https://my.telegram.org/apps)

### Installation

```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Add your credentials

# 2. Start LM Studio
# Open LM Studio → Start local server on port 1234

# 3. Launch platform
docker-compose up -d

# 4. View logs
docker-compose logs -f aggregator

# 5. Access
# Web: http://localhost
# API: http://localhost:8000/docs
```

### Minimum Configuration

```env
# .env
POSTGRES_PASSWORD=your_secure_password
MAPBOX_TOKEN=pk.your_mapbox_token
LLM_MODEL=qwen2.5-7b-instruct
```

## Architecture

```
Internet → Nginx (80) → Frontend (3000) → API (8000) → Database (PostgreSQL + PostGIS)
                                        ↓
                                    LM Studio (localhost:1234)
                                        ↓
                                    Redis (Cache)
```

## API Endpoints

```
GET  /api/events          # List events (filterable)
GET  /api/events/{id}     # Get event details
POST /api/events          # Create event manually

GET  /api/sources         # List data sources
POST /api/sources         # Add source

GET  /api/alerts          # List alert rules
POST /api/alerts          # Create alert

GET  /api/stats           # Platform statistics

WS   /ws/events           # Real-time stream

POST /admin/collect       # Trigger collection
POST /admin/process       # Trigger processing
```

## Data Flow

1. **Collection**: Telegram/RSS → Raw events in database
2. **Processing**: LLM extracts category, threat level, entities, location
3. **Geocoding**: Location text → Coordinates (PostGIS Point)
4. **Storage**: Indexed in PostgreSQL with spatial data
5. **API**: FastAPI serves to frontend
6. **Display**: Mapbox renders on interactive map

## Configuration

### Telegram Setup

```env
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=your_hash
TELEGRAM_PHONE=+1234567890
TELEGRAM_CHANNELS=channel1,channel2
```

First run authentication:
```bash
docker-compose logs -f aggregator
# Follow prompts to enter code sent to your phone
```

### RSS Feeds

```env
RSS_FEEDS=https://feed1.xml,https://feed2.xml
```

### Scheduler

```env
COLLECTION_INTERVAL_MINUTES=5  # Collection frequency
PROCESSING_INTERVAL_MINUTES=2  # LLM processing frequency
```

## Project Structure

```
osint-aggregator/
├── aggregator/              # Python backend
│   ├── src/
│   │   ├── collectors/      # Telegram, RSS, etc.
│   │   ├── processors/      # LLM processing
│   │   ├── api/             # FastAPI routes
│   │   ├── models.py        # SQLAlchemy + PostGIS
│   │   ├── scheduler.py     # Background tasks
│   │   └── main.py          # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Next.js app
├── nginx/                   # Reverse proxy
├── scripts/                 # DB initialization
└── docker-compose.yml
```

## Monitoring

```bash
# Logs
docker-compose logs -f aggregator

# Status
curl http://localhost:8000/health

# Manual triggers
curl -X POST http://localhost:8000/admin/collect
curl -X POST http://localhost:8000/admin/process

# Database
docker-compose exec database psql -U osint -d osint_aggregator
```

## Troubleshooting

### LM Studio Connection

```bash
# Test from host
curl http://localhost:1234/v1/models

# Test from container
docker-compose exec aggregator curl http://host.docker.internal:1234/v1/models
```

### Telegram Re-authentication

```bash
rm -rf aggregator/sessions/*
docker-compose restart aggregator
docker-compose logs -f aggregator
```

### Reset Database

```bash
docker-compose down -v
docker-compose up -d
```

## Security

- Never commit `.env`
- Change default `POSTGRES_PASSWORD`
- Keep `aggregator/sessions/` private
- LM Studio runs locally (no external API)

## License

MIT
