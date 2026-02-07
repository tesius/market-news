import { useTopics } from '@/hooks/useNews'
import { useReadStatus } from '@/hooks/useReadStatus'
import { TopicItem } from './TopicCard'
import { Accordion } from '@/components/ui/accordion'
import { Loader2, Newspaper } from 'lucide-react'

export function NewsFeed() {
  const { data, isLoading } = useTopics()
  const { isRead, markAsRead } = useReadStatus()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!data || data.items.length === 0) {
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

  const handleValueChange = (value: string) => {
    if (value) {
      markAsRead(data.batch_id, Number(value))
    }
  }

  return (
    <Accordion
      type="single"
      collapsible
      className="space-y-2"
      onValueChange={handleValueChange}
    >
      {data.items.map((topic) => (
        <TopicItem
          key={topic.id}
          topic={topic}
          isNew={!isRead(data.batch_id, topic.id)}
        />
      ))}
    </Accordion>
  )
}
