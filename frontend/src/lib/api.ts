import axios from 'axios'
import type {
  BatchInfo,
  Briefing,
  Keyword,
  MarketData,
  RefreshResponse,
  Region,
  TopicSummaryList,
} from '@/types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

// Topic Summaries
export async function fetchTopics(batchId?: string): Promise<TopicSummaryList> {
  const { data } = await api.get('/api/topics', {
    params: batchId ? { batch_id: batchId } : undefined,
  })
  return data
}

export async function fetchTopicsByDateRange(
  daysOffset: number,
  daysLimit: number = 3
): Promise<TopicSummaryList> {
  const { data } = await api.get('/api/topics', {
    params: { days_offset: daysOffset, days_limit: daysLimit },
  })
  return data
}

export async function fetchBatches(): Promise<BatchInfo[]> {
  const { data } = await api.get('/api/batches')
  return data
}

// Keywords
export async function fetchKeywords(): Promise<Keyword[]> {
  const { data } = await api.get('/api/keywords')
  return data
}

export async function createKeyword(payload: {
  topic: string
  region: Region
}): Promise<Keyword> {
  const { data } = await api.post('/api/keywords', payload)
  return data
}

export async function updateKeyword(
  id: number,
  payload: { topic?: string; region?: Region; is_active?: boolean }
): Promise<Keyword> {
  const { data } = await api.patch(`/api/keywords/${id}`, payload)
  return data
}

export async function deleteKeyword(id: number): Promise<void> {
  await api.delete(`/api/keywords/${id}`)
}

// Briefing
export async function fetchBriefing(): Promise<Briefing | null> {
  const { data } = await api.get('/api/briefing')
  return data
}

// Market Data
export async function fetchMarketData(): Promise<MarketData> {
  const { data } = await api.get('/api/market-data')
  return data
}

// Refresh
export async function triggerRefresh(): Promise<RefreshResponse> {
  const { data } = await api.post('/api/refresh')
  return data
}
