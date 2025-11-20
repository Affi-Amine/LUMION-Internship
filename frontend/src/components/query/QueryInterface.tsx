"use client"
import { useState } from 'react'
import { graphragAPI } from '@/lib/api'

export function QueryInterface() {
  const [type, setType] = useState<'local' | 'global' | 'drift'>('local')
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function runQuery() {
    setLoading(true)
    try {
      if (type === 'local') {
        const { data } = await graphragAPI.localQuery(query)
        setResponse(data)
      } else if (type === 'global') {
        const { data } = await graphragAPI.globalQuery(query)
        setResponse(data)
      } else {
        const { data } = await graphragAPI.driftQuery(query, ['Q1','Q2'])
        setResponse(data)
      }
    } catch (e: any) {
      setResponse({ error: e?.message || 'Request failed' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-4 space-y-4">
      <div className="flex gap-2">
        <button className={`px-3 py-1 border ${type==='local'?'bg-black text-white':''}`} onClick={() => setType('local')}>Local</button>
        <button className={`px-3 py-1 border ${type==='global'?'bg-black text-white':''}`} onClick={() => setType('global')}>Global</button>
        <button className={`px-3 py-1 border ${type==='drift'?'bg-black text-white':''}`} onClick={() => setType('drift')}>Drift</button>
      </div>
      <textarea className="w-full border p-2" rows={6} value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ask a question" />
      <button className="px-3 py-1 border" onClick={runQuery} disabled={loading}>{loading ? 'Running...' : 'Run'}</button>
      <pre className="border p-3 whitespace-pre-wrap break-words">{response ? JSON.stringify(response, null, 2) : 'Response will appear here'}</pre>
    </div>
  )
}