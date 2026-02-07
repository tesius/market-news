import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchTopics,
  fetchBatches,
  fetchKeywords,
  createKeyword,
  updateKeyword,
  deleteKeyword,
  fetchBriefing,
  fetchMarketData,
  triggerRefresh,
} from '@/lib/api'
import type { Region } from '@/types'

export function useTopics(batchId?: string) {
  return useQuery({
    queryKey: ['topics', batchId],
    queryFn: () => fetchTopics(batchId),
    refetchInterval: 5 * 60 * 1000,
  })
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
      queryClient.invalidateQueries({ queryKey: ['batches'] })
      queryClient.invalidateQueries({ queryKey: ['briefing'] })
    },
  })
}
