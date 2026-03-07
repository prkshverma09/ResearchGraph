import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import GraphVisualization, {
  buildGraphElements,
  truncateNodeLabel,
} from '@/app/components/GraphVisualization'

const mockApi = vi.hoisted(() => ({
  getPaperWithRelations: vi.fn(),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual('@/lib/api')
  return {
    ...actual,
    api: mockApi,
  }
})

vi.mock('@/app/components/ThemeProvider', () => ({
  useTheme: () => ({
    theme: 'dark',
    toggleTheme: vi.fn(),
  }),
}))

describe('GraphVisualization', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty state when no paper is selected', () => {
    render(<GraphVisualization />)

    expect(screen.getByText('Select a paper to view its graph')).toBeInTheDocument()
  })

  it('renders loading state while graph data is being fetched', async () => {
    mockApi.getPaperWithRelations.mockImplementation(() => new Promise(() => {}))

    render(<GraphVisualization paperId="paper-1" />)

    expect(await screen.findByText('Loading graph...')).toBeInTheDocument()
  })

  it('truncates long node labels and keeps short labels unchanged', () => {
    expect(truncateNodeLabel('short')).toBe('short')
    expect(truncateNodeLabel('abcdefghijklmnopqrstuvwxyz')).toBe('abcdefghijklmnopqrstu…')
  })

  it('maps API graph data into deduplicated nodes and edges', () => {
    const result = buildGraphElements('paper-root', {
      paper: { title: 'Attention Is All You Need' },
      authors: [{ name: 'Unknown author' }, { name: 'Unknown author' }],
      topics: [{ name: 'Unknown topic' }],
      citations: [{ title: 'Long citation title that should be truncated in node label' }],
    })

    expect(result.nodes.length).toBe(4)
    expect(result.edges.length).toBe(3)

    const paperNode = result.nodes.find((node) => node.id === 'paper-root')
    expect(paperNode).toBeDefined()
    expect(paperNode?.data?.fullLabel).toBe('Attention Is All You Need')
    expect(paperNode?.size).toBeGreaterThan(5)

    const citationNode = result.nodes.find((node) => node.id.startsWith('paper-') && node.id !== 'paper-root')
    expect(citationNode).toBeDefined()
    expect(citationNode?.label?.endsWith('…')).toBe(true)
    expect(citationNode?.data?.fullLabel).toContain('Long citation title')
  })
})
