import GraphView from '@/components/graph/GraphView'

export default function Page() {
  return (
    <main className="p-6">
      <h1 className="text-xl font-semibold">Graph Visualization</h1>
      <p className="text-sm text-gray-600">Interactive nodes and edges with zoom/pan</p>
      <div className="mt-4">
        <GraphView />
      </div>
    </main>
  )
}