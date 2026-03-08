'use client'

import { useState } from 'react'
import { useTheme } from './ThemeProvider'
import PaperList from './PaperList'
import IngestionPanel from './IngestionPanel'

type SidebarTab = 'papers' | 'ingest'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  selectedPaperIds?: string[]
  onPaperSelect?: (paperId: string) => void
  onPaperDeselect?: () => void
  onIngestionComplete?: () => void
}

export default function Sidebar({
  isOpen,
  onClose,
  selectedPaperIds = [],
  onPaperSelect,
  onPaperDeselect,
  onIngestionComplete,
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<SidebarTab>('papers')
  const { theme, toggleTheme } = useTheme()

  if (!isOpen) return null

  return (
    <>
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
        onClick={onClose}
      />
      <div className={`fixed lg:static left-0 top-0 h-full w-80 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 z-50 flex flex-col ${isOpen ? '' : 'hidden lg:flex'}`}>
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            ResearchGraph
          </h1>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            <button
              onClick={onClose}
              className="lg:hidden p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
              aria-label="Close sidebar"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="flex border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setActiveTab('papers')}
            className={`flex-1 px-4 py-2 text-sm font-medium ${
              activeTab === 'papers'
                ? 'border-b-2 border-primary-600 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
            }`}
          >
            Papers
          </button>
          <button
            onClick={() => setActiveTab('ingest')}
            className={`flex-1 px-4 py-2 text-sm font-medium ${
              activeTab === 'ingest'
                ? 'border-b-2 border-primary-600 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
            }`}
          >
            Ingest
          </button>
        </div>

        <div className="flex-1 overflow-hidden">
          {activeTab === 'papers' ? (
            <PaperList
              selectedPaperIds={selectedPaperIds}
              onPaperSelect={onPaperSelect}
              onPaperDeselect={onPaperDeselect}
            />
          ) : (
            <div className="h-full overflow-y-auto">
              <IngestionPanel onIngestionComplete={onIngestionComplete} />
            </div>
          )}
        </div>
      </div>
    </>
  )
}
