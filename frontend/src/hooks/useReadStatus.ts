import { useState, useCallback } from 'react'

const STORAGE_KEY = 'market-news-read'

function getReadIds(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? new Set(JSON.parse(raw)) : new Set()
  } catch {
    return new Set()
  }
}

function saveReadIds(ids: Set<string>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]))
}

export function useReadStatus() {
  const [readIds, setReadIds] = useState(getReadIds)

  const markAsRead = useCallback((batchId: string, topicId: number) => {
    const key = `${batchId}:${topicId}`
    setReadIds((prev) => {
      if (prev.has(key)) return prev
      const next = new Set(prev)
      next.add(key)
      saveReadIds(next)
      return next
    })
  }, [])

  const isRead = useCallback(
    (batchId: string, topicId: number) => readIds.has(`${batchId}:${topicId}`),
    [readIds]
  )

  return { isRead, markAsRead }
}
