import {
  useQuery,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import {
  fetchTopics,
  fetchTopicsByDateRange,
  fetchBatches,
  fetchKeywords,
  createKeyword,
  updateKeyword,
  deleteKeyword,
  fetchBriefing,
  fetchMarketData,
  triggerRefresh,
} from '@/lib/api'
import type { Region, TopicSummary, BatchGroup } from '@/types'

export function useTopics(batchId?: string) {
  return useQuery({
    queryKey: ['topics', batchId],
    queryFn: () => fetchTopics(batchId),
    refetchInterval: 5 * 60 * 1000,
  })
}

export function useInfiniteTopics(daysPerPage: number = 3) {
  return useInfiniteQuery({
    queryKey: ['topics-infinite'],
    queryFn: ({ pageParam = 0 }) => fetchTopicsByDateRange(pageParam, daysPerPage),
    initialPageParam: 0,
    getNextPageParam: (lastPage, _allPages, lastPageParam) => {
      if (lastPage.has_more) {
        return (lastPageParam as number) + daysPerPage
      }
      return undefined
    },
    refetchInterval: 5 * 60 * 1000,
  })
}

const SESSION_LABELS: Record<string, string> = {
  morning: '오전 브리핑',
  midday: '오후 브리핑',
  evening: '저녁 브리핑',
}

function formatDateLabel(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diff = Math.round((today.getTime() - target.getTime()) / (1000 * 60 * 60 * 24))

  if (diff === 0) return '오늘'
  if (diff === 1) return '어제'

  const weekdays = ['일', '월', '화', '수', '목', '금', '토']
  const month = date.getMonth() + 1
  const day = date.getDate()
  const weekday = weekdays[date.getDay()]
  return `${month}월 ${day}일(${weekday})`
}

export function groupByBatch(topics: TopicSummary[]): BatchGroup[] {
  const map = new Map<string, TopicSummary[]>()
  for (const topic of topics) {
    const existing = map.get(topic.batch_id)
    if (existing) {
      existing.push(topic)
    } else {
      map.set(topic.batch_id, [topic])
    }
  }

  const groups: BatchGroup[] = []
  for (const [batchId, batchTopics] of map) {
    // batch_id format: "2026-02-07_morning"
    const parts = batchId.split('_')
    const date = parts[0] || ''
    const sessionKey = parts[1] || ''

    groups.push({
      batch_id: batchId,
      date: formatDateLabel(date),
      session: SESSION_LABELS[sessionKey] || sessionKey,
      topics: batchTopics,
    })
  }

  // Sort by batch_id descending (newest first)
  groups.sort((a, b) => b.batch_id.localeCompare(a.batch_id))
  return groups
}

export function useBatches() {
  return useQuery({
    queryKey: ['batches'],
    queryFn: fetchBatches,
  })
}

export function useKeywords() {
  return useQuery({
    queryKey: ['keywords'],
    queryFn: fetchKeywords,
  })
}

export function useCreateKeyword() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createKeyword,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keywords'] })
      // Poll for new topic summary (background processing takes a few seconds)
      const poll = setInterval(() => {
        queryClient.invalidateQueries({ queryKey: ['topics'] })
        queryClient.invalidateQueries({ queryKey: ['topics-infinite'] })
      }, 5000)
      setTimeout(() => clearInterval(poll), 60000)
    },
  })
}

export function useUpdateKeyword() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      ...payload
    }: {
      id: number
      topic?: string
      region?: Region
      is_active?: boolean
    }) => updateKeyword(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['keywords'] }),
  })
}

export function useDeleteKeyword() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteKeyword,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['keywords'] }),
  })
}

export function useBriefing() {
  return useQuery({
    queryKey: ['briefing'],
    queryFn: fetchBriefing,
    refetchInterval: 10 * 60 * 1000,
  })
}

export function useMarketData() {
  return useQuery({
    queryKey: ['market-data'],
    queryFn: fetchMarketData,
    refetchInterval: 5 * 60 * 1000,
  })
}

export function useRefresh() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: triggerRefresh,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topics'] })
      queryClient.invalidateQueries({ queryKey: ['topics-infinite'] })
      queryClient.invalidateQueries({ queryKey: ['batches'] })
      queryClient.invalidateQueries({ queryKey: ['briefing'] })
    },
  })
}
