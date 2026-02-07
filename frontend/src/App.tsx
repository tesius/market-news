import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TopBar } from '@/components/TopBar'
import { BriefingPanel } from '@/components/BriefingPanel'
import { NewsFeed } from '@/components/NewsFeed'
import { KeywordModal } from '@/components/KeywordModal'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,
      retry: 2,
    },
  },
})

function Dashboard() {
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopBar onSettingsClick={() => setSettingsOpen(true)} />

      <main className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8">
        {/* Briefing */}
        <BriefingPanel />

        {/* Topic Summaries */}
        <div className="mt-5">
          <NewsFeed />
        </div>
      </main>

      <KeywordModal open={settingsOpen} onOpenChange={setSettingsOpen} />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  )
}
