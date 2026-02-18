# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Market News is a personal investment dashboard that aggregates US/Korean economic news, applies AI sentiment analysis via Google Gemini 2.5 Flash, and provides Korean-language briefings. Single-user, no auth.

## Architecture

**Monorepo** with separate `backend/` (Python/FastAPI) and `frontend/` (React/TypeScript/Vite) directories.

### Backend (`backend/`)
- **FastAPI** async-first, SQLAlchemy ORM with aiosqlite (SQLite)
- **Config**: Pydantic settings from `.env` (`backend/app/config.py`)
- **Routers**: `app/routers/` — news, keywords, briefing, market endpoints (all prefixed `/api`)
- **Services**: `app/services/` — business logic layer
  - `news_collector.py` — fetches from Finnhub (US primary), CNBC RSS (fallback), Naver (KR); deduplicates by URL + 55% similarity threshold
  - `ai_processor.py` — consolidates articles per keyword via single Gemini call; 6s rate limit between requests
  - `briefing_generator.py` — daily top-3 must-reads + cross-market themes
  - `market_data.py` — yfinance for indices (Nasdaq, S&P500, KOSPI, KOSDAQ, USD/KRW)
  - `article_scraper.py` — BeautifulSoup HTML body extraction
- **Scheduler** (`app/scheduler.py`): APScheduler, 3x daily (08:00, 13:00, 18:00 KST) collect→consolidate→briefing pipeline; 03:00 KST cleanup of data >30 days
- **DB models** in `app/models.py`: Keywords, Articles, TopicSummaries, Briefings

### Frontend (`frontend/`)
- **React 19 + TypeScript + Vite** with Tailwind CSS v4 and shadcn/ui (Radix primitives)
- **State**: TanStack Query with auto-refetch (5min topics/market, 10min briefing)
- **API client**: axios in `src/lib/api.ts`, base URL from `VITE_API_URL` env var
- **Key components**: `TopBar`, `BriefingPanel`, `NewsFeed` (infinite scroll), `TopicCard` (accordion), `TickerTape`, `KeywordModal`
- **Hooks**: `src/hooks/` — `useNews.ts` (all API query hooks), `useTheme.ts`, `useReadStatus.ts`
- **Sentiment colors**: Red = Bullish (강세), Blue = Bearish (약세) — Korean market convention

### Deployment
- **Backend**: fly.io (Docker, Tokyo region `nrt`), SQLite on mounted volume `/data`
- **Frontend**: GitHub Pages via Actions (`.github/workflows/deploy-frontend.yml`), base path `/market-news/`

## Build & Dev Commands

### Backend
```bash
cd backend
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env  # fill in API keys
uv run uvicorn app.main:app --reload  # http://localhost:8000
```
Swagger docs at http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # tsc -b && vite build
npm run lint     # eslint
npm run preview  # preview production build
```

### Deployment
```bash
fly deploy                    # backend to fly.io
git push origin main          # frontend auto-deploys via GitHub Actions
```

## Environment Variables (backend/.env)

Required: `GEMINI_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `FINNHUB_API_KEY`
Optional: `DATABASE_URL` (default: local SQLite), `CORS_ORIGINS` (comma-separated), `ENV`

## Key Patterns

- All AI output is in Korean (prompts instruct Gemini to respond in Korean for quant investors)
- One Gemini call per keyword (not per article) — articles are batched and consolidated
- `POST /api/refresh` triggers the full collect→process→briefing pipeline manually
- Adding a keyword via `POST /api/keywords` triggers background news collection for that keyword
- Default 7 keywords are seeded on first run in `app/main.py`
- No tests exist yet
- DB migrations via Alembic (`backend/alembic/`)
