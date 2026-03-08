import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import GraphVisualization, {
  buildGraphElements,
  truncateNodeLabel,
} from '@/app/components/GraphVisualization'
import type { ReactNode } from 'react'

const mockApi = vi.hoisted(() => ({
  getGraphSubgraph: vi.fn(),
}))

const mockGraphControls = vi.hoisted(() => ({
  attachRef: true,
  zoomIn: vi.fn(),
  zoomOut: vi.fn(),
  fitNodesInView: vi.fn(),
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

vi.mock('reagraph', async () => {
  const React = await vi.importActual<typeof import('react')>('react')

  const GraphCanvas = React.forwardRef(
    ({ children }: { children?: ReactNode }, ref: React.Ref<any>) => {
      React.useImperativeHandle(
        ref,
        () => (
          mockGraphControls.attachRef
            ? {
                zoomIn: mockGraphControls.zoomIn,
                zoomOut: mockGraphControls.zoomOut,
                fitNodesInView: mockGraphControls.fitNodesInView,
              }
            : null
        ),
        []
      )

      return <div data-testid="mock-graph-canvas">{children}</div>
    }
  )

  GraphCanvas.displayName = 'MockGraphCanvas'
  return { GraphCanvas }
})

describe('GraphVisualization', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGraphControls.attachRef = true
  })

  it('renders empty state when no paper is selected', () => {
    render(<GraphVisualization />)

    expect(screen.getByText('Select one or more papers to view their graph')).toBeInTheDocument()
  })

  it('renders loading state while graph data is being fetched', async () => {
    mockApi.getGraphSubgraph.mockImplementation(() => new Promise(() => {}))

    render(<GraphVisualization paperIds={['paper-1']} />)

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

  it('clears previous graph immediately when selection shrinks and shows latest selection only', async () => {
    let pendingSecondResponseResolve: ((value: any) => void) | undefined

    mockApi.getGraphSubgraph
      .mockResolvedValueOnce({
        papers: [{ id: 'paper:a' }, { id: 'paper:b' }],
        mode: 'semantic',
        nodes: [{ id: 'paper:a', label: 'Paper A', type: 'paper' }],
        edges: [],
        counts: { nodes: 1, edges: 0 },
      })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            pendingSecondResponseResolve = resolve
          })
      )

    const { rerender } = render(<GraphVisualization paperIds={['paper:a', 'paper:b']} />)

    await waitFor(() => {
      expect(mockApi.getGraphSubgraph).toHaveBeenCalledWith(['paper:a', 'paper:b'])
    })

    rerender(<GraphVisualization paperIds={['paper:a']} />)

    expect(await screen.findByText('Loading graph...')).toBeInTheDocument()
    expect(mockApi.getGraphSubgraph).toHaveBeenLastCalledWith(['paper:a'])

    if (pendingSecondResponseResolve) {
      pendingSecondResponseResolve({
        papers: [{ id: 'paper:a' }],
        mode: 'semantic',
        nodes: [{ id: 'paper:a', label: 'Paper A', type: 'paper' }],
        edges: [],
        counts: { nodes: 1, edges: 0 },
      })
    }
  })

  it('invokes graph camera controls when +, -, and Fit are clicked', async () => {
    mockApi.getGraphSubgraph.mockResolvedValue({
      papers: [{ id: 'paper:a' }],
      mode: 'semantic',
      nodes: [{ id: 'paper:a', label: 'Paper A', type: 'paper' }],
      edges: [],
      counts: { nodes: 1, edges: 0 },
    })

    render(<GraphVisualization paperIds={['paper:a']} />)

    const zoomInBtn = await screen.findByLabelText('Zoom in')
    const zoomOutBtn = screen.getByLabelText('Zoom out')
    const fitBtn = screen.getByLabelText('Fit graph')

    await waitFor(() => {
      expect(zoomInBtn).toBeEnabled()
      expect(zoomOutBtn).toBeEnabled()
      expect(fitBtn).toBeEnabled()
    })

    fireEvent.click(zoomInBtn)
    fireEvent.click(zoomOutBtn)
    const fitCallCount = mockGraphControls.fitNodesInView.mock.calls.length
    fireEvent.click(fitBtn)

    expect(mockGraphControls.zoomIn).toHaveBeenCalledTimes(1)
    expect(mockGraphControls.zoomOut).toHaveBeenCalledTimes(1)
    expect(mockGraphControls.fitNodesInView).toHaveBeenCalledTimes(fitCallCount + 1)
  })

  it('keeps controls disabled when graph ref is not available', async () => {
    mockGraphControls.attachRef = false
    mockApi.getGraphSubgraph.mockResolvedValue({
      papers: [{ id: 'paper:a' }],
      mode: 'semantic',
      nodes: [{ id: 'paper:a', label: 'Paper A', type: 'paper' }],
      edges: [],
      counts: { nodes: 1, edges: 0 },
    })

    render(<GraphVisualization paperIds={['paper:a']} />)

    const zoomInBtn = await screen.findByLabelText('Zoom in')
    const zoomOutBtn = screen.getByLabelText('Zoom out')
    const fitBtn = screen.getByLabelText('Fit graph')

    expect(zoomInBtn).toBeDisabled()
    expect(zoomOutBtn).toBeDisabled()
    expect(fitBtn).toBeDisabled()

    fireEvent.click(zoomInBtn)
    fireEvent.click(zoomOutBtn)
    fireEvent.click(fitBtn)

    expect(mockGraphControls.zoomIn).not.toHaveBeenCalled()
    expect(mockGraphControls.zoomOut).not.toHaveBeenCalled()
  })
})
