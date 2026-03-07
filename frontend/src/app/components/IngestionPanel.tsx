'use client'

import { useState, useRef, DragEvent } from 'react'
import { api } from '@/lib/api'

interface IngestionPanelProps {
  onIngestionComplete?: () => void
}

export default function IngestionPanel({ onIngestionComplete }: IngestionPanelProps) {
  const [arxivId, setArxivId] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [ingestingArxiv, setIngestingArxiv] = useState(false)
  const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragEnter = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const pdfFile = files.find((f) => f.type === 'application/pdf' || f.name.endsWith('.pdf'))

    if (pdfFile) {
      await handleFileUpload(pdfFile)
    } else {
      setStatus({ type: 'error', message: 'Please drop a PDF file' })
    }
  }

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      await handleFileUpload(file)
    }
  }

  const handleFileUpload = async (file: File) => {
    setUploading(true)
    setStatus(null)

    try {
      const result = await api.ingestPDF(file)
      setStatus({
        type: 'success',
        message: `Paper ingested successfully! Created ${result.nodes_created} nodes and ${result.edges_created} edges.`,
      })
      onIngestionComplete?.()
    } catch (error) {
      setStatus({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to ingest PDF',
      })
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleArxivIngest = async () => {
    if (!arxivId.trim()) {
      setStatus({ type: 'error', message: 'Please enter an arXiv ID' })
      return
    }

    setIngestingArxiv(true)
    setStatus(null)

    try {
      const result = await api.ingestArxiv(arxivId.trim())
      setStatus({
        type: 'success',
        message: `Paper ingested successfully! Created ${result.nodes_created} nodes and ${result.edges_created} edges.`,
      })
      setArxivId('')
      onIngestionComplete?.()
    } catch (error) {
      setStatus({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to ingest arXiv paper',
      })
    } finally {
      setIngestingArxiv(false)
    }
  }

  return (
    <div className="p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
        Ingest Papers
      </h2>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
            Upload PDF
          </label>
          <div
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-primary-400 dark:hover:border-primary-600'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileInput}
              className="hidden"
              id="pdf-upload"
            />
            <label
              htmlFor="pdf-upload"
              className="cursor-pointer block"
            >
              <div className="text-gray-600 dark:text-gray-400 mb-2">
                {isDragging ? 'Drop PDF here' : 'Drag and drop PDF or click to browse'}
              </div>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? 'Uploading...' : 'Select PDF'}
              </button>
            </label>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
            Ingest from arXiv
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={arxivId}
              onChange={(e) => setArxivId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleArxivIngest()}
              placeholder="e.g., 2401.00001"
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              onClick={handleArxivIngest}
              disabled={ingestingArxiv}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {ingestingArxiv ? 'Ingesting...' : 'Ingest'}
            </button>
          </div>
        </div>

        {status && (
          <div
            className={`p-3 rounded-md ${
              status.type === 'success'
                ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300'
                : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300'
            }`}
          >
            {status.message}
          </div>
        )}
      </div>
    </div>
  )
}
