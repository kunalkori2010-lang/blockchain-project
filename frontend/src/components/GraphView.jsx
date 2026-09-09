import { useMemo, useState } from 'react'
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow'
import 'reactflow/dist/style.css'

function layout(graph, suspect) {
  // BFS layers from suspect for a readable left→right flow
  const adj = {}
  graph.edges.forEach((e) => {
    adj[e.source] = adj[e.source] || []
    adj[e.source].push(e.target)
  })
  const layer = {}
  const q = []
  if (suspect) { layer[suspect] = 0; q.push(suspect) }
  while (q.length) {
    const u = q.shift()
    for (const v of (adj[u] || [])) {
      if (!(v in layer)) { layer[v] = (layer[u] || 0) + 1; q.push(v) }
    }
  }
  const buckets = {}
  Object.entries(layer).forEach(([id, l]) => {
    const L = Math.min(l, 4)
    buckets[L] = buckets[L] || []
    buckets[L].push(id)
  })
  const pos = {}
  Object.entries(buckets).forEach(([l, ids]) => {
    ids.forEach((id, i) => {
      pos[id] = { x: Number(l) * 260, y: i * 90 - (ids.length * 45) }
    })
  })
  graph.nodes.forEach((n) => {
    if (!pos[n.id]) pos[n.id] = { x: 900, y: Math.random() * 400 }
  })
  return pos
}

export default function GraphView({ graph, suspect, onSelect }) {
  const [sel, setSel] = useState(null)
  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] }
    const pos = layout(graph, suspect)
    const nodes = graph.nodes.map((n) => ({
      id: n.id,
      position: pos[n.id],
      data: { label: `${n.type === 'suspect' ? '🎯 ' : n.type === 'exchange' ? '🏦 ' : n.type === 'flagged' ? '🚩 ' : '👛 '}${n.label}` },
      style: {
        background: n.type === 'suspect' ? '#4f46e5' : n.type === 'exchange' ? '#065f46' : n.type === 'flagged' ? '#7f1d1d' : '#1e293b',
        color: '#fff', border: '1px solid #475569', borderRadius: 12, padding: 8, minWidth: 150,
        fontWeight: n.type === 'suspect' ? 800 : 500,
      },
    }))
    const edges = graph.edges.map((e) => ({
      id: e.id + e.source.slice(0, 6), source: e.source, target: e.target,
      label: e.label, animated: true, style: { stroke: '#6366f1' },
    }))
    return { nodes, edges }
  }, [graph, suspect])

  return (
    <div className="grid md:grid-cols-3 gap-4">
      <div className="md:col-span-2 h-[460px] rounded-2xl overflow-hidden border border-slate-800 bg-slate-900">
        <ReactFlow nodes={nodes} edges={edges}
          onNodeClick={(_, n) => { setSel(n.id); onSelect && onSelect(n.id) }} fitView>
          <Background /><Controls /><MiniMap />
        </ReactFlow>
      </div>
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 text-sm">
        <div className="font-bold mb-2">Node inspector</div>
        {!sel ? <div className="text-slate-400 text-xs">Click any wallet / exchange node to inspect. Suspect is violet, exchanges green, flagged red.</div> :
          <div>
            <div className="break-all font-mono text-[11px] bg-slate-800 rounded-lg p-2">{sel}</div>
            <div className="text-xs text-slate-400 mt-2">Incoming / outgoing edges and tx hashes appear in the explorer table below. Use Generate Report for the full evidence pack.</div>
          </div>}
        <div className="mt-4 text-xs text-slate-400">
          <div>Nodes: <b className="text-slate-200">{graph?.nodes?.length || 0}</b> · Edges: <b className="text-slate-200">{graph?.edges?.length || 0}</b></div>
          <div className="mt-1">Layout: BFS layers from suspect wallet (fund-flow direction).</div>
        </div>
      </div>
    </div>
  )
}
