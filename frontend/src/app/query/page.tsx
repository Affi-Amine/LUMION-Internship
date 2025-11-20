import { QueryInterface } from '@/components/query/QueryInterface'

export default function Page() {
  return (
    <main className="p-6">
      <h1 className="text-xl font-semibold">GraphRAG Query</h1>
      <QueryInterface />
    </main>
  )
}