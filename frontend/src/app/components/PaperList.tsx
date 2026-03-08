'use client'

import { useState, useEffect } from 'react'
import { api, PaperSearchResult } from '@/lib/api'

interface PaperListProps {
  selectedPaperIds?: string[]
  onPaperSelect?: (paperId: string) => void
  onPaperDeselect?: () => void
}

export default function PaperList({
  selectedPaperIds = [],
  onPaperSelect,
  onPaperDeselect,
}: PaperListProps) {
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

  const handleDelete = async (e: React.MouseEvent, paperId: string) => {
    e.stopPropagation()
    if (window.confirm('Are you sure you want to delete this paper?')) {
      try {
        setLoading(true)
        await api.deletePaper(paperId)
        // If the deleted paper was selected, this component doesn't own that state, 
        // but we can at least refresh the list. Parent should ideally handle the graph reset.
        await loadPapers()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete paper')
        setLoading(false)
      }
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

  const handleCardKeyDown = (e: React.KeyboardEvent, paperId: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onPaperSelect?.(paperId)
    }
  }

  const handlePaperTabClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement
    if (!target.closest('[data-paper-card="true"]')) {
      onPaperDeselect?.()
    }
  }

  return (
    <div
      className="h-full flex flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700"
      onClick={handlePaperTabClick}
    >
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
          <div className="space-y-3" role="listbox" aria-label="Paper list">
            {papers.map((paper) => {
              const isSelected = selectedPaperIds.includes(paper.paper_id)
              const cardClasses = isSelected
                ? 'border-primary-400 bg-primary-100/80 dark:bg-primary-900/50 shadow-sm'
                : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
              const titleClasses = isSelected
                ? 'text-primary-900 dark:text-primary-100'
                : 'text-gray-900 dark:text-gray-100'
              const abstractClasses = isSelected
                ? 'text-primary-800 dark:text-primary-200'
                : 'text-gray-600 dark:text-gray-400'
              const scoreClasses = isSelected
                ? 'text-primary-700 dark:text-primary-300'
                : 'text-gray-500 dark:text-gray-500'

              return (
                <div
                  key={paper.paper_id}
                  data-paper-card="true"
                  role="option"
                  aria-selected={isSelected}
                  tabIndex={0}
                  onClick={() => onPaperSelect?.(paper.paper_id)}
                  onKeyDown={(e) => handleCardKeyDown(e, paper.paper_id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors relative group focus:outline-none focus:ring-2 focus:ring-primary-500 ${cardClasses}`}
                >
                  {isSelected && (
                    <span
                      aria-hidden="true"
                      className="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg bg-primary-500"
                    />
                  )}
                  <div className="flex justify-between items-start gap-2">
                    <h3 className={`font-semibold text-sm mb-1 line-clamp-2 ${titleClasses}`}>
                      {paper.title}
                    </h3>
                    <button
                      onClick={(e) => handleDelete(e, paper.paper_id)}
                      className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity p-1 -mt-1 -mr-1"
                      title="Delete paper"
                    >
                      🗑️
                    </button>
                  </div>
                  <p className={`text-xs line-clamp-2 ${abstractClasses}`}>
                    {paper.abstract}
                  </p>
                  <div className={`mt-2 text-xs ${scoreClasses}`}>
                    Score: {paper.relevance_score.toFixed(2)}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
