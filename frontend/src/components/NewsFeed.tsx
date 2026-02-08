import { useRef, useCallback, useEffect, useMemo } from 'react'
import { useInfiniteTopics, groupByBatch } from '@/hooks/useNews'
import { useReadStatus } from '@/hooks/useReadStatus'
import { TopicItem } from './TopicCard'
import { Accordion } from '@/components/ui/accordion'
import { Loader2, Newspaper, ChevronDown, CheckCircle2 } from 'lucide-react'

export function NewsFeed() {
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfiniteTopics()
  const { isRead, markAsRead } = useReadStatus()
  const sentinelRef = useRef<HTMLDivElement>(null)

  // Intersection Observer for infinite scroll
  const handleObserver = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries
      if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
        fetchNextPage()
      }
    },
    [hasNextPage, isFetchingNextPage, fetchNextPage]
  )

  useEffect(() => {
    const el = sentinelRef.current
    if (!el) return

    const observer = new IntersectionObserver(handleObserver, {
      rootMargin: '200px',
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [handleObserver])

  // Flatten all pages and group by batch
  const batchGroups = useMemo(() => {
    if (!data?.pages) return []
    const allTopics = data.pages.flatMap((page) => page.items)
    return groupByBatch(allTopics)
  }, [data])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (batchGroups.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-20 text-center">
        <Newspaper className="h-10 w-10 text-muted-foreground/50" />
        <p className="text-base text-muted-foreground">
          아직 수집된 뉴스가 없습니다.
          <br />
          상단의 새로고침 버튼을 눌러 수집을 시작하세요.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {batchGroups.map((group) => (
        <section key={group.batch_id}>
          {/* Batch section header */}
          <div className="mb-3 flex items-center gap-2">
            <h3 className="text-sm font-semibold text-muted-foreground">
              {group.date}
            </h3>
            <span className="text-sm text-muted-foreground/60">
              {group.session}
            </span>
            <div className="h-px flex-1 bg-border/50" />
          </div>

          <Accordion
            type="single"
            collapsible
            className="space-y-2"
            onValueChange={(value) => {
              if (value) {
                markAsRead(group.batch_id, Number(value))
              }
            }}
          >
            {group.topics.map((topic) => (
              <TopicItem
                key={topic.id}
                topic={topic}
                isNew={!isRead(group.batch_id, topic.id)}
              />
            ))}
          </Accordion>
        </section>
      ))}

      {/* Scroll sentinel + loading / end state */}
      <div ref={sentinelRef} className="flex items-center justify-center py-6">
        {isFetchingNextPage ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : hasNextPage ? (
          <button
            onClick={() => fetchNextPage()}
            className="flex items-center gap-2 rounded-lg border border-border/50 px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <ChevronDown className="h-4 w-4" />
            이전 뉴스 더보기
          </button>
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground/50">
            <CheckCircle2 className="h-4 w-4" />
            모든 뉴스를 불러왔습니다
          </div>
        )}
      </div>
    </div>
  )
}
