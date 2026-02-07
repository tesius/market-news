# Market News - 개인 투자 뉴스 대시보드

미국/한국 경제 뉴스를 자동 수집하고, Gemini AI로 키워드별 통합 분석을 제공하는 개인 투자 대시보드.

## 주요 기능

- **키워드 기반 뉴스 수집** - 관심 키워드별로 미국(Finnhub, CNBC RSS) / 한국(Naver API) 뉴스 자동 수집
- **AI 통합 분석** - 키워드당 수집된 기사들을 Gemini 2.5 Flash가 하나의 한국어 브리핑으로 통합 요약
- **감성 분석** - 각 토픽별 강세/약세/중립 판단 및 관련 티커 추출
- **일일 브리핑** - Top 3 Must Read 선정 및 교차 시장 테마 분석
- **실시간 지수** - Nasdaq, S&P 500, KOSPI, KOSDAQ, USD/KRW 시세 표시
- **아코디언 UI** - 헤드라인을 한눈에 훑고, 클릭하면 상세 요약 확인
- **다크/라이트 모드** - 테마 전환 지원
- **NEW 배지** - 읽지 않은 토픽 구분

## 기술 스택

| 영역 | 기술 |
|---|---|
| Backend | Python 3.11, FastAPI (async), SQLAlchemy + aiosqlite |
| AI | Gemini 2.5 Flash (`google-genai` SDK) |
| Frontend | React, Vite, TypeScript, Tailwind CSS v4, shadcn/ui |
| 상태관리 | TanStack Query |
| 스케줄러 | APScheduler (08:00, 18:00 KST) |
| 배포 | Backend → fly.io, Frontend → GitHub Pages |

## 뉴스 소스

| 지역 | 소스 | 비고 |
|---|---|---|
| US | Finnhub API (Primary) | 무료 60 req/min |
| US | CNBC RSS (Fallback) | Finnhub 실패 시 자동 전환 |
| KR | Naver Search API | Client ID/Secret 필요 |

## 시작하기

### 사전 요구사항

- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python 패키지 관리)

### API 키 발급

- [Gemini API Key](https://aistudio.google.com/apikey)
- [Finnhub API Key](https://finnhub.io/register)
- [Naver Developers](https://developers.naver.com/) - 검색 API 애플리케이션 등록

### 백엔드 설정

```bash
cd backend

# 가상환경 생성 및 의존성 설치
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 실제 API 키 입력

# 서버 실행
uv run uvicorn app.main:app --reload
```

서버가 http://localhost:8000 에서 실행됩니다.

### 프론트엔드 설정

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

http://localhost:5173 에서 대시보드를 확인할 수 있습니다.

## 사용법

1. 첫 실행 시 기본 키워드 7개가 자동 생성됩니다
2. 상단 새로고침 버튼을 눌러 뉴스 수집을 시작합니다
3. 수집 완료 후 키워드별 통합 분석이 아코디언 형태로 표시됩니다
4. 설정(톱니바퀴) 버튼으로 키워드를 추가/삭제할 수 있습니다
5. 키워드 추가 시 해당 키워드의 뉴스가 자동으로 수집됩니다

## 프로젝트 구조

```
market-news/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 엔트리포인트
│   │   ├── config.py            # 환경변수 설정
│   │   ├── database.py          # SQLAlchemy 엔진
│   │   ├── models.py            # DB 모델
│   │   ├── schemas.py           # Pydantic 스키마
│   │   ├── scheduler.py         # APScheduler 설정
│   │   ├── routers/             # API 엔드포인트
│   │   └── services/            # 비즈니스 로직
│   │       ├── news_collector.py    # 뉴스 수집
│   │       ├── ai_processor.py      # Gemini AI 분석
│   │       ├── briefing_generator.py # 일일 브리핑
│   │       ├── market_data.py       # 시장 지수
│   │       └── article_scraper.py   # 기사 본문 추출
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/          # UI 컴포넌트
│       ├── hooks/               # React 훅
│       ├── lib/                 # API 클라이언트
│       └── types/               # TypeScript 타입
├── fly.toml                     # fly.io 배포 설정
└── PRD.md                       # 기획 문서
```

## API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/topics` | 키워드별 통합 요약 목록 |
| GET | `/api/batches` | 수집 배치 히스토리 |
| GET | `/api/keywords` | 키워드 목록 |
| POST | `/api/keywords` | 키워드 추가 (자동 수집 트리거) |
| PATCH | `/api/keywords/{id}` | 키워드 수정 |
| DELETE | `/api/keywords/{id}` | 키워드 삭제 |
| GET | `/api/briefing` | 오늘의 브리핑 |
| GET | `/api/market-data` | 시장 지수 데이터 |
| POST | `/api/refresh` | 전체 수집 수동 트리거 |

## API 사용량 (무료 쿼터)

하루 2회 스케줄 + 키워드 7개 기준:

| API | 무료 한도 | 일일 사용량 |
|---|---|---|
| Gemini 2.5 Flash | 250 RPD | ~16회 (6.4%) |
| Finnhub | 60 req/min | ~8회/일 |
| Naver Search | 25,000/일 | ~6회/일 |
