import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
})

export const customersAPI = {
  list: (params?: any) => api.get('/api/customers', { params }),
  get: (id: string) => api.get(`/api/customers/${id}`),
}

export const graphragAPI = {
  localQuery: (query: string, history?: any[]) => api.post('/api/graphrag/query/local', { query, history }),
  globalQuery: (query: string, history?: any[]) => api.post('/api/graphrag/query/global', { query, history }),
  driftQuery: (query: string, periods: string[]) => api.post('/api/graphrag/query/drift', { query, periods }),
}

export const graphAPI = {
  export: (dataset?: string) => api.get('/api/graph/export', { params: { dataset: dataset || 'crm' } }),
  exportCode: () => api.get('/api/graph/export', { params: { dataset: 'code' } }),
  neighbors: (id: string, depth: number = 1) => api.get(`/api/graph/neighbors/${id}`, { params: { depth } }),
}
