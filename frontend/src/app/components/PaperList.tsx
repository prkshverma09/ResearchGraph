'use client'

import { useState, useEffect } from 'react'
import { api, PaperSearchResult } from '@/lib/api'

interface PaperListProps {
  onPaperSelect?: (paperId: string) => void
}

export default function PaperList({ onPaperSelect }: PaperListProps) {
  const [papers, setPapers] = useState<PaperSearchResult[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPapers()
  }, [])

  const loadPapers = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.listPapers()
      setPapers(response.papers)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load papers')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadPapers()
      return
    }

    try {
      setLoading(true)
      setError(null)
      const response = await api.search(searchQuery, 20)
      setPapers(response.papers)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
          Papers
        </h2>
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search papers..."
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '...' : 'Search'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {error && (
          <div className="text-red-600 dark:text-red-400 text-sm mb-4">{error}</div>
        )}
        {loading && papers.length === 0 ? (
          <div className="text-gray-500 dark:text-gray-400 text-center py-8">
            Loading papers...
          </div>
        ) : papers.length === 0 ? (
          <div className="text-gray-500 dark:text-gray-400 text-center py-8">
            No papers found
          </div>
        ) : (
          <div className="space-y-3">
            {papers.map((paper) => (
              <div
                key={paper.paper_id}
                onClick={() => onPaperSelect?.(paper.paper_id)}
                className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
              >
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-1 line-clamp-2">
                  {paper.title}
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                  {paper.abstract}
                </p>
                <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                  Score: {paper.relevance_score.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
