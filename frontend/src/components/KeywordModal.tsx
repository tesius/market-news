import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  useKeywords,
  useCreateKeyword,
  useUpdateKeyword,
  useDeleteKeyword,
} from '@/hooks/useNews'
import { Trash2, Plus } from 'lucide-react'
import type { Region } from '@/types'

interface KeywordModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function KeywordModal({ open, onOpenChange }: KeywordModalProps) {
  const { data: keywords, isLoading } = useKeywords()
  const createKeyword = useCreateKeyword()
  const updateKeyword = useUpdateKeyword()
  const deleteKeyword = useDeleteKeyword()

  const [newTopic, setNewTopic] = useState('')
  const [newRegion, setNewRegion] = useState<Region>('US')

  const handleAdd = () => {
    if (!newTopic.trim()) return
    createKeyword.mutate(
      { topic: newTopic.trim(), region: newRegion },
      { onSuccess: () => setNewTopic('') }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Keyword Management</DialogTitle>
        </DialogHeader>

        {/* Add New */}
        <div className="flex gap-2">
          <Input
            placeholder="New keyword..."
            value={newTopic}
            onChange={(e) => setNewTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            className="flex-1"
          />
          <div className="flex gap-1">
            <Button
              variant={newRegion === 'US' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setNewRegion('US')}
            >
              US
            </Button>
            <Button
              variant={newRegion === 'KR' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setNewRegion('KR')}
            >
              KR
            </Button>
          </div>
          <Button
            size="icon"
            onClick={handleAdd}
            disabled={createKeyword.isPending || !newTopic.trim()}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <Separator />

        {/* Keyword List */}
        {isLoading ? (
          <div className="py-4 text-center text-sm text-muted-foreground">
            Loading...
          </div>
        ) : !keywords || keywords.length === 0 ? (
          <div className="py-4 text-center text-sm text-muted-foreground">
            No keywords yet.
          </div>
        ) : (
          <div className="space-y-2">
            {keywords.map((kw) => (
              <div
                key={kw.id}
                className="flex items-center gap-3 rounded-lg border border-border p-3"
              >
                <Switch
                  checked={kw.is_active}
                  onCheckedChange={(checked) =>
                    updateKeyword.mutate({ id: kw.id, is_active: checked })
                  }
                />
                <div className="flex-1">
                  <span
                    className={`text-sm font-medium ${
                      !kw.is_active ? 'text-muted-foreground line-through' : ''
                    }`}
                  >
                    {kw.topic}
                  </span>
                </div>
                <Badge variant="outline" className="text-[10px]">
                  {kw.region}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => deleteKeyword.mutate(kw.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
