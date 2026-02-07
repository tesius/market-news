import { useMarketData } from '@/hooks/useNews'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export function TickerTape() {
  const { data, isLoading } = useMarketData()

  if (isLoading || !data) {
    return (
      <div className="flex items-center gap-6 overflow-hidden">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-4 w-24 animate-pulse rounded bg-muted" />
        ))}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-6 overflow-x-auto scrollbar-hide">
      {data.indices.map((idx) => {
        const isPositive = idx.change > 0
        const isNegative = idx.change < 0

        return (
          <div key={idx.symbol} className="flex shrink-0 items-center gap-1.5 text-sm">
            <span className="font-medium text-muted-foreground">{idx.name}</span>
            <span className="font-mono font-semibold">
              {idx.price.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
            <span
              className={`flex items-center gap-0.5 text-xs font-medium ${
                isPositive
                  ? 'text-red-400'
                  : isNegative
                    ? 'text-blue-400'
                    : 'text-muted-foreground'
              }`}
            >
              {isPositive ? (
                <TrendingUp className="h-3 w-3" />
              ) : isNegative ? (
                <TrendingDown className="h-3 w-3" />
              ) : (
                <Minus className="h-3 w-3" />
              )}
              {isPositive ? '+' : ''}
              {idx.change_pct.toFixed(2)}%
            </span>
          </div>
        )
      })}
    </div>
  )
}
