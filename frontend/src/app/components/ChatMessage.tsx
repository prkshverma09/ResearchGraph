'use client'

import { Source } from '@/lib/api'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  isStreaming?: boolean
}

export default function ChatMessage({ role, content, sources, isStreaming }: ChatMessageProps) {
  const isUser = role === 'user'

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
              <div
                key={idx}
                className="text-xs text-primary-600 dark:text-primary-400 hover:underline cursor-pointer"
              >
                {source.title || source.paper_id || `Source ${idx + 1}`}
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
