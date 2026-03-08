'use client'

import {
  Component,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type CSSProperties,
  type ErrorInfo,
  type ReactNode,
} from 'react'
import dynamic from 'next/dynamic'
import type { GraphCanvasRef, GraphEdge, GraphNode, InternalGraphNode, Theme } from 'reagraph'
import { useTheme } from './ThemeProvider'

const ReagraphCanvas = dynamic(
  () => import('reagraph').then((mod) => mod.GraphCanvas),
  { ssr: false }
) as ComponentType<any>

type NodeType = 'paper' | 'author' | 'topic'
type LinkType = 'cites' | 'authored_by' | 'belongs_to'

interface RelationRecord {
  id?: string
  name?: string
  title?: string
}

interface PaperGraphResponse {
  paper?: {
    title?: string
  }
  authors?: RelationRecord[]
  topics?: RelationRecord[]
  citations?: RelationRecord[]
}

interface GraphVisualizationProps {
  paperIds?: string[]
  width?: number
  height?: number
}

interface HoveredNodeInfo {
  id: string
  type: NodeType
  fullLabel: string
}

interface GraphCanvasErrorBoundaryProps {
  children: ReactNode
}

interface GraphCanvasErrorBoundaryState {
  hasError: boolean
}

class GraphCanvasErrorBoundary extends Component<
  GraphCanvasErrorBoundaryProps,
  GraphCanvasErrorBoundaryState
> {
  constructor(props: GraphCanvasErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): GraphCanvasErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Graph renderer crashed:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-full w-full flex items-center justify-center text-sm text-amber-700 dark:text-amber-300 bg-amber-50/80 dark:bg-amber-950/30">
          Graph renderer failed to load. Please reselect a paper.
        </div>
      )
    }

    return this.props.children
  }
}

const NODE_COLORS: Record<NodeType, string> = {
  paper: '#0ea5e9',
  author: '#10b981',
  topic: '#f59e0b',
}

const EDGE_COLORS: Record<LinkType, string> = {
  cites: '#0ea5e9',
  authored_by: '#10b981',
  belongs_to: '#f59e0b',
}

const BASE_LIGHT_THEME: Theme = {
  canvas: { background: '#ffffff' },
  node: {
    fill: '#7CA0AB',
    activeFill: '#1DE9AC',
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.2,
    label: {
      color: '#2A6475',
      stroke: '#ffffff',
      activeColor: '#1DE9AC',
    },
    subLabel: {
      color: '#dddddd',
      stroke: 'transparent',
      activeColor: '#1DE9AC',
    },
  },
  lasso: { border: '1px solid #55aaff', background: 'rgba(75, 160, 255, 0.1)' },
  ring: { fill: '#D8E6EA', activeFill: '#1DE9AC' },
  edge: {
    fill: '#D8E6EA',
    activeFill: '#1DE9AC',
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.1,
    label: {
      stroke: '#ffffff',
      color: '#2A6475',
      activeColor: '#1DE9AC',
      fontSize: 6,
    },
  },
  arrow: { fill: '#D8E6EA', activeFill: '#1DE9AC' },
  cluster: {
    stroke: '#D8E6EA',
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.1,
    label: {
      stroke: '#ffffff',
      color: '#2A6475',
    },
  },
}

const BASE_DARK_THEME: Theme = {
  canvas: { background: '#1E2026' },
  node: {
    fill: '#7A8C9E',
    activeFill: '#1DE9AC',
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.2,
    label: {
      stroke: '#1E2026',
      color: '#ACBAC7',
      activeColor: '#1DE9AC',
    },
    subLabel: {
      stroke: '#1E2026',
      color: '#ACBAC7',
      activeColor: '#1DE9AC',
    },
  },
  lasso: { border: '1px solid #55aaff', background: 'rgba(75, 160, 255, 0.1)' },
  ring: { fill: '#54616D', activeFill: '#1DE9AC' },
  edge: {
    fill: '#474B56',
    activeFill: '#1DE9AC',
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.1,
    label: {
      stroke: '#1E2026',
      color: '#ACBAC7',
      activeColor: '#1DE9AC',
      fontSize: 6,
    },
  },
  arrow: { fill: '#474B56', activeFill: '#1DE9AC' },
  cluster: {
    stroke: '#474B56',
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.1,
    label: {
      stroke: '#1E2026',
      color: '#ACBAC7',
    },
  },
}

const MAX_NODE_LABEL_LENGTH = 22

export function truncateNodeLabel(label: string, maxLength = MAX_NODE_LABEL_LENGTH): string {
  const normalized = label.trim()
  if (normalized.length <= maxLength) {
    return normalized
  }

  return `${normalized.slice(0, maxLength - 1).trimEnd()}…`
}

function slugify(value: string): string {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')

  return slug || 'unknown'
}

function getValidNodeId(rawId: string | undefined, fallbackPrefix: string, fallbackLabel: string): string {
  if (typeof rawId === 'string' && rawId.trim().length > 0) {
    return rawId.trim()
  }

  return `${fallbackPrefix}-${slugify(fallbackLabel)}`
}

function getTypeLabel(type: NodeType): string {
  switch (type) {
    case 'paper':
      return 'Paper'
    case 'author':
      return 'Author'
    case 'topic':
      return 'Topic'
    default:
      return 'Node'
  }
}

function createGraphTheme(appTheme: 'light' | 'dark'): Theme {
  if (appTheme === 'dark') {
    return {
      ...BASE_DARK_THEME,
      canvas: { ...BASE_DARK_THEME.canvas, background: '#020617' },
      node: {
        ...BASE_DARK_THEME.node,
        label: {
          ...BASE_DARK_THEME.node.label,
          color: '#dbeafe',
          activeColor: '#ffffff',
          stroke: '#0f172a',
        },
      },
      edge: {
        ...BASE_DARK_THEME.edge,
        label: { ...BASE_DARK_THEME.edge.label, fontSize: 5 },
      },
    }
  }

  return {
    ...BASE_LIGHT_THEME,
    canvas: { ...BASE_LIGHT_THEME.canvas, background: '#f8fafc' },
    node: {
      ...BASE_LIGHT_THEME.node,
      label: {
        ...BASE_LIGHT_THEME.node.label,
        color: '#0f172a',
        activeColor: '#1e293b',
        stroke: '#ffffff',
      },
    },
    edge: {
      ...BASE_LIGHT_THEME.edge,
      label: { ...BASE_LIGHT_THEME.edge.label, fontSize: 5 },
    },
  }
}

function addNode(
  nodesById: Map<string, GraphNode>,
  type: NodeType,
  nodeId: string,
  fullLabel: string
): void {
  if (nodesById.has(nodeId)) {
    return
  }

  nodesById.set(nodeId, {
    id: nodeId,
    label: truncateNodeLabel(fullLabel),
    size: type === 'paper' ? 5.5 : 4.3,
    fill: NODE_COLORS[type],
    data: {
      fullLabel,
      type,
    },
  })
}

function addEdge(
  edgesById: Map<string, GraphEdge>,
  type: LinkType,
  source: string,
  target: string
): void {
  const edgeId = `${type}-${source}-${target}`
  if (edgesById.has(edgeId)) {
    return
  }

  edgesById.set(edgeId, {
    id: edgeId,
    source,
    target,
    size: type === 'cites' ? 1.2 : 1,
    fill: EDGE_COLORS[type],
  })
}

export function buildGraphElements(
  paperId: string,
  data: PaperGraphResponse
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodesById = new Map<string, GraphNode>()
  const edgesById = new Map<string, GraphEdge>()

  const primaryLabel = data.paper?.title?.trim() || paperId
  const primaryId = getValidNodeId(paperId, 'paper', primaryLabel)
  addNode(nodesById, 'paper', primaryId, primaryLabel)

  for (const author of data.authors || []) {
    const authorLabel = (author.name || 'Unknown author').trim()
    const authorId = getValidNodeId(author.id, 'author', authorLabel)
    addNode(nodesById, 'author', authorId, authorLabel)
    addEdge(edgesById, 'authored_by', primaryId, authorId)
  }

  for (const topic of data.topics || []) {
    const topicLabel = (topic.name || 'Unknown topic').trim()
    const topicId = getValidNodeId(topic.id, 'topic', topicLabel)
    addNode(nodesById, 'topic', topicId, topicLabel)
    addEdge(edgesById, 'belongs_to', primaryId, topicId)
  }

  for (const citation of data.citations || []) {
    const citationLabel = (citation.title || 'Unknown citation').trim()
    const citationId = getValidNodeId(citation.id, 'paper', citationLabel)
    addNode(nodesById, 'paper', citationId, citationLabel)
    addEdge(edgesById, 'cites', primaryId, citationId)
  }

  return {
    nodes: [...nodesById.values()],
    edges: [...edgesById.values()],
  }
}

export default function GraphVisualization({
  paperIds = [],
  width,
  height,
}: GraphVisualizationProps) {
  const { theme } = useTheme()
  const graphRef = useRef<GraphCanvasRef | null>(null)

  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [edges, setEdges] = useState<GraphEdge[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [hoveredNode, setHoveredNode] = useState<HoveredNodeInfo | null>(null)

  const graphTheme = useMemo(() => createGraphTheme(theme), [theme])

  useEffect(() => {
    let isCancelled = false

    const loadGraphData = async (ids: string[]) => {
      setLoading(true)
      setError(null)

      try {
        const { api } = await import('@/lib/api')
        const data = await api.getGraphSubgraph(ids)
        if (isCancelled) {
          return
        }

        setNodes(data.nodes || [])
        setEdges(data.edges || [])
      } catch (err) {
        if (!isCancelled) {
          console.error('Failed to load graph data:', err)
          setError('Failed to load graph data')
          setNodes([])
          setEdges([])
        }
      } finally {
        if (!isCancelled) {
          setLoading(false)
        }
      }
    }

    if (paperIds.length === 0) {
      setNodes([])
      setEdges([])
      setError(null)
      setSelectedNodeId(null)
      setHoveredNode(null)
      setLoading(false)
      return
    }

    void loadGraphData(paperIds)

    return () => {
      isCancelled = true
    }
  }, [paperIds])

  useEffect(() => {
    if (nodes.length === 0) {
      return
    }

    const timer = window.setTimeout(() => {
      graphRef.current?.fitNodesInView(undefined, { animated: true })
    }, 220)

    return () => {
      window.clearTimeout(timer)
    }
  }, [nodes, paperIds])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
        Loading graph...
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-600 dark:text-red-400">
        {error}
      </div>
    )
  }

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
        Select one or more papers to view their graph
      </div>
    )
  }

  const containerStyle: CSSProperties = {
    width: width ? `${width}px` : '100%',
    height: height ? `${height}px` : '100%',
  }

  return (
    <div
      className="w-full h-full border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-slate-50 dark:bg-slate-950 relative"
      style={containerStyle}
      data-testid="graph-panel"
    >
      <GraphCanvasErrorBoundary key={paperIds.join('|') || 'graph-canvas'}>
        <ReagraphCanvas
          ref={graphRef}
          nodes={nodes}
          edges={edges}
          theme={graphTheme}
          layoutType="forceDirected2d"
          layoutOverrides={{
            centerInertia: 0.65,
            nodeStrength: -180,
            linkDistance: 165,
          }}
          labelType="nodes"
          draggable={true}
          cameraMode="pan"
          minDistance={120}
          maxDistance={14000}
          edgeArrowPosition="end"
          edgeInterpolation="curved"
          selections={selectedNodeId ? [selectedNodeId] : []}
          onNodeClick={(node: InternalGraphNode) => {
            setSelectedNodeId(node.id)
          }}
          onNodePointerOver={(node: InternalGraphNode) => {
            const fullLabel = typeof node.data?.fullLabel === 'string' ? node.data.fullLabel : node.label || node.id
            const type = (node.data?.type || 'paper') as NodeType
            setHoveredNode({ id: node.id, fullLabel, type })
          }}
          onNodePointerOut={() => {
            setHoveredNode(null)
          }}
          onCanvasClick={() => {
            setSelectedNodeId(null)
            setHoveredNode(null)
          }}
        />

        <div className="absolute top-2 right-2 flex gap-1.5 z-20">
          <button
            type="button"
            onClick={() => graphRef.current?.zoomIn()}
            className="h-7 w-7 rounded-md bg-white/90 dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm hover:bg-white dark:hover:bg-slate-800 transition-colors"
            aria-label="Zoom in"
            title="Zoom in"
          >
            +
          </button>
          <button
            type="button"
            onClick={() => graphRef.current?.zoomOut()}
            className="h-7 w-7 rounded-md bg-white/90 dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm hover:bg-white dark:hover:bg-slate-800 transition-colors"
            aria-label="Zoom out"
            title="Zoom out"
          >
            -
          </button>
          <button
            type="button"
            onClick={() => graphRef.current?.fitNodesInView(undefined, { animated: true })}
            className="h-7 px-2 rounded-md bg-white/90 dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 transition-colors"
            aria-label="Fit graph"
            title="Fit graph"
          >
            Fit
          </button>
        </div>

        {hoveredNode && (
          <div className="absolute left-2 bottom-2 max-w-[85%] rounded-md border border-slate-200 dark:border-slate-700 bg-white/95 dark:bg-slate-900/95 px-2.5 py-1.5 text-xs shadow-md z-20">
            <div className="font-semibold text-slate-900 dark:text-slate-100">{hoveredNode.fullLabel}</div>
            <div className="text-slate-600 dark:text-slate-300">
              {getTypeLabel(hoveredNode.type)} · drag node to reposition
            </div>
          </div>
        )}
      </GraphCanvasErrorBoundary>
    </div>
  )
}
