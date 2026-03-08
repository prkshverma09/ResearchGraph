'use client'

import { Source } from '@/lib/api'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  isStreaming?: boolean
  onSourceClick?: (paperId: string) => void
}

export default function ChatMessage({
  role,
  content,
  sources,
  isStreaming,
  onSourceClick,
}: ChatMessageProps) {
  const isUser = role === 'user'
  const getSourceLabel = (source: Source, idx: number): string => {
    const title = (source.title || '').trim()
    if (title && title.toLowerCase() !== 'unknown') {
      return title
    }
    const paperId = (source.paper_id || '').trim()
    if (paperId) {
      return paperId
    }
    return `Source ${idx + 1}`
  }
  const getExternalLabel = (url: string): string => {
    const lowered = url.toLowerCase()
    if (lowered.includes('arxiv.org')) return 'arXiv'
    if (lowered.includes('doi.org')) return 'DOI'
    return 'Link'
  }

  return (
    <div className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white font-bold flex-shrink-0">
          AI
        </div>
      )}
      <div className={`max-w-3xl ${isUser ? 'order-1' : ''}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
          }`}
        >
          <div className="whitespace-pre-wrap">{content}</div>
          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
          )}
        </div>
        {!isUser && sources && sources.length > 0 && (
          <div className="mt-2 space-y-1">
            <div className="text-xs text-gray-500 dark:text-gray-400 font-semibold">
              Sources:
            </div>
            {sources.map((source, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs">
                {source.paper_id && onSourceClick ? (
                  <button
                    type="button"
                    className="text-primary-600 dark:text-primary-400 hover:underline"
                    onClick={() => onSourceClick(source.paper_id as string)}
                  >
                    {getSourceLabel(source, idx)}
                  </button>
                ) : (
                  <span className="text-primary-600 dark:text-primary-400">
                    {getSourceLabel(source, idx)}
                  </span>
                )}
                {source.external_url && (
                  <a
                    href={source.external_url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-gray-500 dark:text-gray-400 hover:underline"
                  >
                    {getExternalLabel(source.external_url)}
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-400 flex items-center justify-center text-white font-bold flex-shrink-0">
          U
        </div>
      )}
    </div>
  )
}
