'use client'

'use client'

import { useEffect, useRef, useState } from 'react'
import dynamic from 'next/dynamic'

const ForceGraph2D = dynamic(
  () => import('react-force-graph-2d'),
  { ssr: false }
)

interface Node {
  id: string
  label: string
  type: 'paper' | 'author' | 'topic'
  group?: number
}

interface Link {
  source: string | Node
  target: string | Node
  type: 'cites' | 'authored_by' | 'belongs_to'
}

interface GraphVisualizationProps {
  paperId?: string
  width?: number
  height?: number
}

export default function GraphVisualization({
  paperId,
  width = 800,
  height = 600,
}: GraphVisualizationProps) {
  const [nodes, setNodes] = useState<Node[]>([])
  const [links, setLinks] = useState<Link[]>([])
  const [loading, setLoading] = useState(false)
  const graphRef = useRef<any>()

  useEffect(() => {
    if (paperId) {
      loadGraphData(paperId)
    }
  }, [paperId])

  const loadGraphData = async (id: string) => {
    setLoading(true)
    try {
      const { api } = await import('@/lib/api')
      const data = await api.getPaperWithRelations(id)

      const graphNodes: Node[] = [
        {
          id: id,
          label: data.paper.title || id,
          type: 'paper',
          group: 1,
        },
      ]

      const graphLinks: Link[] = []

      data.authors.forEach((author: any) => {
        const authorId = author.id || `author-${author.name}`
        graphNodes.push({
          id: authorId,
          label: author.name,
          type: 'author',
          group: 2,
        })
        graphLinks.push({
          source: id,
          target: authorId,
          type: 'authored_by',
        })
      })

      data.topics.forEach((topic: any) => {
        const topicId = topic.id || `topic-${topic.name}`
        graphNodes.push({
          id: topicId,
          label: topic.name,
          type: 'topic',
          group: 3,
        })
        graphLinks.push({
          source: id,
          target: topicId,
          type: 'belongs_to',
        })
      })

      data.citations.forEach((citation: any) => {
        const citationId = citation.id || `paper-${citation.title}`
        graphNodes.push({
          id: citationId,
          label: citation.title || citationId,
          type: 'paper',
          group: 1,
        })
        graphLinks.push({
          source: id,
          target: citationId,
          type: 'cites',
        })
      })

      setNodes(graphNodes)
      setLinks(graphLinks)
    } catch (error) {
      console.error('Failed to load graph data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getNodeColor = (node: Node) => {
    switch (node.type) {
      case 'paper':
        return '#3b82f6'
      case 'author':
        return '#10b981'
      case 'topic':
        return '#f59e0b'
      default:
        return '#6b7280'
    }
  }

  const getLinkColor = (link: Link) => {
    switch (link.type) {
      case 'cites':
        return '#3b82f6'
      case 'authored_by':
        return '#10b981'
      case 'belongs_to':
        return '#f59e0b'
      default:
        return '#6b7280'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
        Loading graph...
      </div>
    )
  }

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
        Select a paper to view its graph
      </div>
    )
  }

  return (
    <div className="w-full h-full border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <ForceGraph2D
        ref={graphRef}
        graphData={{ nodes, links }}
        nodeLabel={(node: Node) => node.label}
        nodeColor={getNodeColor}
        linkColor={getLinkColor}
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.25}
        width={width}
        height={height}
        nodeCanvasObject={(node: Node, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const label = node.label
          const fontSize = 12 / globalScale
          ctx.font = `${fontSize}px Sans-Serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillStyle = '#000'
          ctx.fillText(label, node.x || 0, (node.y || 0) + 8)
        }}
        onNodeClick={(node: Node) => {
          console.log('Node clicked:', node)
        }}
      />
    </div>
  )
}
