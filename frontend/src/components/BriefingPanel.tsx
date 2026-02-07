import { useBriefing } from '@/hooks/useNews'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { TrendingUp, TrendingDown, Sparkles } from 'lucide-react'

export function BriefingPanel() {
  const { data: briefing, isLoading } = useBriefing()

  if (isLoading || !briefing) return null

  const sentiment = briefing.overall_sentiment

  return (
    <section className="rounded-xl border border-border/50 bg-card p-5 sm:p-6">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-yellow-400" />
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Today&apos;s Briefing
        </h2>
      </div>

      {/* Sentiment Bar */}
      {sentiment && (
        <div className="mb-4">
          <div className="mb-2 flex h-2 w-full overflow-hidden rounded-full">
            <div
              className="bg-emerald-500 transition-all"
              style={{ width: `${sentiment.bullish_pct}%` }}
            />
            <div
              className="bg-slate-500 transition-all"
              style={{ width: `${sentiment.neutral_pct}%` }}
            />
            <div
              className="bg-red-500 transition-all"
              style={{ width: `${sentiment.bearish_pct}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-1 text-emerald-400">
              <TrendingUp className="h-3 w-3" />
              {sentiment.bullish_pct}%
            </span>
            <span>{sentiment.neutral_pct}% Neutral</span>
            <span className="flex items-center gap-1 text-red-400">
              <TrendingDown className="h-3 w-3" />
              {sentiment.bearish_pct}%
            </span>
          </div>
          {sentiment.summary && (
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              {sentiment.summary}
            </p>
          )}
        </div>
      )}

      {/* Must Reads */}
      {briefing.must_reads && briefing.must_reads.length > 0 && (
        <>
          <Separator className="my-4 opacity-50" />
          <div className="space-y-3">
            {briefing.must_reads.map((mr, i) => (
              <div key={mr.article_id} className="flex gap-3">
                <Badge
                  variant="outline"
                  className="mt-0.5 h-5 w-5 shrink-0 justify-center rounded-full p-0 font-mono text-[10px]"
                >
                  {i + 1}
                </Badge>
                <div>
                  <p className="text-sm font-medium leading-snug">{mr.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {mr.why_important}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Cross-Market Themes */}
      {briefing.cross_market_themes &&
        briefing.cross_market_themes.length > 0 && (
          <>
            <Separator className="my-4 opacity-50" />
            <div className="space-y-1">
              {briefing.cross_market_themes.map((theme, i) => (
                <p key={i} className="text-xs text-muted-foreground">
                  &bull; {theme}
                </p>
              ))}
            </div>
          </>
        )}
    </section>
  )
}
