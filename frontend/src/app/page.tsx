'use client'

import { useState, useRef, useEffect } from 'react'
import ChatMessage from './components/ChatMessage'
import Sidebar from './components/Sidebar'
import GraphVisualization from './components/GraphVisualization'
import { api, Source } from '@/lib/api'

export default function Home() {
  const [messages, setMessages] = useState<Array<{
    role: 'user' | 'assistant'
    content: string
    sources?: Source[]
  }>>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessions, setSessions] = useState<Array<{ id: string; created_at: string }>>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null)
  const [filterSelectedOnly, setFilterSelectedOnly] = useState(false)
  const [showGraph, setShowGraph] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    loadSessions()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const loadSessions = async () => {
    try {
      const response = await api.listSessions("user-1")
      setSessions(response.sessions)
    } catch (error) {
      console.error('Failed to load sessions:', error)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    if (filterSelectedOnly && !selectedPaperId) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Select a paper first, or turn off "Selected paper only" to search across all papers.',
        },
      ])
      return
    }

    const selectedPaperIds = selectedPaperId ? [selectedPaperId] : []

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)
    setIsStreaming(true)
    setStreamingContent('')

    try {
      let currentSessionId = sessionId
      if (!currentSessionId) {
        const newSession = await api.createSession('user-1')
        currentSessionId = newSession.id
        setSessionId(currentSessionId)
        await loadSessions()
      }

      let fullAnswer = ''
      let sources: Source[] = []
      let finalSessionId = currentSessionId

      try {
        for await (const event of api.askStream(userMessage, currentSessionId, {
          filterSelectedOnly,
          selectedPaperIds,
        })) {
          if (event.type === 'session_id') {
            finalSessionId = event.data
            setSessionId(finalSessionId)
          } else if (event.type === 'node') {
            const nodeData = event.data
            if (nodeData?.final_answer) {
              const newContent = nodeData.final_answer
              setStreamingContent(newContent)
              fullAnswer = newContent
            } else if (nodeData?.messages && Array.isArray(nodeData.messages)) {
              const lastMessage = nodeData.messages[nodeData.messages.length - 1]
              if (lastMessage?.content) {
                const newContent = lastMessage.content
                setStreamingContent(newContent)
                fullAnswer = newContent
              }
            }
          } else if (event.type === 'chunk' && event.chunk) {
            const newContent = fullAnswer + event.chunk
            setStreamingContent(newContent)
            fullAnswer = newContent
          }
        }

        const response = await api.ask(userMessage, finalSessionId, {
          filterSelectedOnly,
          selectedPaperIds,
        })
        if (response.sources.length > 0) {
          sources = response.sources
        }
        if (response.answer && !fullAnswer) {
          fullAnswer = response.answer
          setStreamingContent(fullAnswer)
        }
        finalSessionId = response.session_id
        setSessionId(finalSessionId)
      } catch (streamError) {
        console.error('Streaming error, falling back to non-streaming:', streamError)
        const response = await api.ask(userMessage, currentSessionId, {
          filterSelectedOnly,
          selectedPaperIds,
        })
        fullAnswer = response.answer
        sources = response.sources
        finalSessionId = response.session_id
        setSessionId(finalSessionId)
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: fullAnswer || streamingContent,
          sources,
        },
      ])
      setStreamingContent('')
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${error instanceof Error ? error.message : 'Failed to get response'}`,
        },
      ])
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
      setStreamingContent('')
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSessionChange = async (newSessionId: string) => {
    if (newSessionId === 'new') {
      setSessionId(null)
      setMessages([])
      return
    }

    try {
      const session = await api.getSession(newSessionId)
      setSessionId(session.id)
      setMessages([])
    } catch (error) {
      console.error('Failed to load session:', error)
    }
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        selectedPaperId={selectedPaperId}
        onPaperSelect={(paperId) => {
          setSelectedPaperId(paperId)
          setShowGraph(true)
        }}
        onPaperDeselect={() => {
          setSelectedPaperId(null)
          setShowGraph(false)
        }}
        onIngestionComplete={() => {
        }}
      />

      <div className="flex-1 flex flex-col">
        <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
              aria-label="Toggle sidebar"
            >
              ☰
            </button>
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 hidden sm:block">
              ResearchGraph Assistant
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={sessionId || 'new'}
              onChange={(e) => handleSessionChange(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="new">New Session</option>
              {sessions.map((session) => (
                <option key={session.id} value={session.id}>
                  Session {new Date(session.created_at).toLocaleDateString()}
                </option>
              ))}
            </select>
            <button
              onClick={() => setShowGraph(!showGraph)}
              className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700"
            >
              {showGraph ? 'Hide Graph' : 'Show Graph'}
            </button>
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden">
          <div className={`flex-1 flex flex-col ${showGraph ? 'lg:w-2/3' : 'w-full'}`}>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && (
                <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                  <div className="text-center">
                    <h2 className="text-2xl font-semibold mb-2">Welcome to ResearchGraph</h2>
                    <p>Ask me anything about research papers, citations, or authors!</p>
                  </div>
                </div>
              )}

              {messages.map((msg, idx) => (
                <ChatMessage
                  key={idx}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                />
              ))}

              {isStreaming && streamingContent && (
                <ChatMessage
                  role="assistant"
                  content={streamingContent}
                  isStreaming={true}
                />
              )}

              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-900">
              <div className="mb-2 flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input
                    type="checkbox"
                    checked={filterSelectedOnly}
                    onChange={(e) => setFilterSelectedOnly(e.target.checked)}
                    disabled={isLoading}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  Selected paper only
                </label>
                {filterSelectedOnly && (
                  <span className="text-xs text-primary-700 dark:text-primary-300">
                    {selectedPaperId ? `Using: ${selectedPaperId}` : 'No paper selected'}
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about research papers..."
                  rows={3}
                  disabled={isLoading}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none disabled:opacity-50"
                />
                <button
                  onClick={handleSend}
                  disabled={isLoading || !input.trim() || (filterSelectedOnly && !selectedPaperId)}
                  className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed self-end"
                >
                  {isLoading ? 'Sending...' : 'Send'}
                </button>
              </div>
            </div>
          </div>

          {showGraph && (
            <div className="hidden lg:block lg:w-1/3 border-l border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-900">
              <GraphVisualization paperId={selectedPaperId || undefined} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
