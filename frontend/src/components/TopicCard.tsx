import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import {
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion'
import {
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  ChevronUp,
  Newspaper,
} from 'lucide-react'
import type { TopicSummary } from '@/types'

interface TopicItemProps {
  topic: TopicSummary
  isNew?: boolean
}

const sentimentConfig = {
  Bullish: {
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/20',
    dotColor: 'bg-red-400',
    icon: TrendingUp,
    label: '강세',
  },
  Bearish: {
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
    dotColor: 'bg-blue-400',
    icon: TrendingDown,
    label: '약세',
  },
  Neutral: {
    color: 'text-slate-400',
    bg: 'bg-slate-500/10',
    border: 'border-slate-500/20',
    dotColor: 'bg-slate-400',
    icon: Minus,
    label: '중립',
  },
}

export function TopicItem({ topic, isNew }: TopicItemProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false)

  const sentiment = topic.sentiment ? sentimentConfig[topic.sentiment] : null
  const SentimentIcon = sentiment?.icon

  return (
    <AccordionItem
      value={String(topic.id)}
      className={`rounded-xl border bg-card px-5 sm:px-6 ${
        sentiment?.border ?? 'border-border/50'
      }`}
    >
      {/* Collapsed: Headline row */}
      <AccordionTrigger className="gap-3 py-4 hover:no-underline [&>svg]:hidden">
        <div className="flex w-full items-center gap-3">
          {/* Sentiment indicator dot */}
          {sentiment && (
            <span
              className={`mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full ${sentiment.dotColor}`}
            />
          )}

          <div className="min-w-0 flex-1 text-left">
            {/* Headline */}
            <h2 className="flex items-center gap-2 text-lg font-bold leading-snug tracking-tight sm:text-xl">
              <span>{topic.headline}</span>
              {isNew && (
                <Badge className="shrink-0 bg-blue-500 px-1.5 py-0 text-[10px] font-semibold text-white hover:bg-blue-500">
                  NEW
                </Badge>
              )}
            </h2>
            {/* Meta line */}
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <Badge variant="outline" className="text-[11px] font-normal">
                {topic.region}
              </Badge>
              <span className="text-sm text-muted-foreground">
                {topic.keyword_tag}
              </span>
              <span className="text-sm text-muted-foreground">&middot;</span>
              <span className="text-sm text-muted-foreground">
                {topic.article_count}개 기사
              </span>
              {sentiment && SentimentIcon && (
                <>
                  <span className="text-sm text-muted-foreground">&middot;</span>
                  <span
                    className={`inline-flex items-center gap-1 text-sm font-medium ${sentiment.color}`}
                  >
                    <SentimentIcon className="h-3.5 w-3.5" />
                    {sentiment.label}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </AccordionTrigger>

      {/* Expanded: Summary + tickers + sources */}
      <AccordionContent className="pb-5">
        {/* Summary */}
        <div className="space-y-4 text-base leading-8 text-muted-foreground sm:text-[17px]">
          {topic.summary.split('\n\n').map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
        </div>

        {/* Tickers */}
        {topic.related_tickers.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {topic.related_tickers.map((ticker) => (
              <Badge
                key={ticker}
                variant="secondary"
                className="font-mono text-xs"
              >
                {ticker}
              </Badge>
            ))}
          </div>
        )}

        {/* Source Articles */}
        {topic.source_articles.length > 0 && (
          <div className="mt-5">
            <button
              onClick={(e) => {
                e.stopPropagation()
                setSourcesOpen(!sourcesOpen)
              }}
              className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <Newspaper className="h-4 w-4" />
              <span>출처 기사 {topic.source_articles.length}건</span>
              {sourcesOpen ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>

            {sourcesOpen && (
              <ul className="mt-3 space-y-2 border-t border-border/30 pt-3">
                {topic.source_articles.map((article) => (
                  <li key={article.id} className="flex items-start gap-2">
                    <span className="mt-0.5 shrink-0 text-xs text-muted-foreground/60">
                      {article.source}
                    </span>
                    <a
                      href={article.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      <span className="line-clamp-1">{article.title}</span>
                      <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 opacity-50" />
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </AccordionContent>
    </AccordionItem>
  )
}
