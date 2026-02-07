import { Radar, Settings, RefreshCw, Sun, Moon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { TickerTape } from './TickerTape'
import { useRefresh } from '@/hooks/useNews'
import { useTheme } from '@/hooks/useTheme'

interface TopBarProps {
  onSettingsClick: () => void
}

export function TopBar({ onSettingsClick }: TopBarProps) {
  const refresh = useRefresh()
  const { dark, toggle } = useTheme()

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center gap-4 px-4 lg:px-6">
        {/* Logo */}
        <div className="flex shrink-0 items-center gap-2">
          <Radar className="h-5 w-5 text-primary" />
          <span className="text-lg font-bold tracking-tight">Market News</span>
        </div>

        {/* Ticker Tape */}
        <div className="hidden min-w-0 flex-1 overflow-hidden md:block">
          <TickerTape />
        </div>

        {/* Actions */}
        <div className="ml-auto flex shrink-0 items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refresh.mutate(undefined)}
            disabled={refresh.isPending}
          >
            <RefreshCw
              className={`h-4 w-4 ${refresh.isPending ? 'animate-spin' : ''}`}
            />
          </Button>
          <Button variant="ghost" size="icon" onClick={toggle}>
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
          <Button variant="ghost" size="icon" onClick={onSettingsClick}>
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Mobile Ticker */}
      <div className="border-t border-border px-4 py-2 md:hidden">
        <TickerTape />
      </div>
    </header>
  )
}
