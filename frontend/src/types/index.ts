export type Region = 'US' | 'KR'
export type Sentiment = 'Bullish' | 'Bearish' | 'Neutral'
export type BriefingSession = 'morning' | 'midday' | 'evening'

export interface Keyword {
  id: number
  topic: string
  region: Region
  is_active: boolean
  created_at: string
}

export interface SourceArticle {
  id: number
  title: string
  link: string
  source: string
}

export interface TopicSummary {
  id: number
  keyword_tag: string
  region: Region
  batch_id: string
  headline: string
  summary: string
  sentiment: Sentiment | null
  related_tickers: string[]
  source_articles: SourceArticle[]
  article_count: number
  created_at: string
}

export interface TopicSummaryList {
  items: TopicSummary[]
  batch_id: string
}

export interface MustRead {
  article_id: number
  title: string
  why_important: string
  impact_analysis: string
}

export interface OverallSentiment {
  bullish_pct: number
  bearish_pct: number
  neutral_pct: number
  summary: string
}

export interface Briefing {
  id: number
  date: string
  session: BriefingSession
  overall_sentiment: OverallSentiment | null
  must_reads: MustRead[] | null
  cross_market_themes: string[] | null
  created_at: string
}

export interface IndexData {
  symbol: string
  name: string
  price: number
  change: number
  change_pct: number
}

export interface MarketData {
  indices: IndexData[]
  updated_at: string
}

export interface RefreshResponse {
  status: string
  articles_collected: number
  articles_processed: number
  message: string
}

export interface BatchInfo {
  batch_id: string
  topic_count: number
  created_at: string
}
