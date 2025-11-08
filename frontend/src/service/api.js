const BASE = import.meta.env.VITE_API_BASE || ''

export async function hello() {
    const res = await fetch(`${BASE}/api/hello`)
    return res.json()
}

export async function echo(message) {
  const r = await fetch(`${BASE}/api/echo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  })
  return r.json()
}

export const listUsers = () => 
    fetch(`${BASE}/api/users`).then(r=>r.json())

export const createUser = (p) =>
    fetch(`${BASE}/api/users`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(p)
    }).then(r=>r.json())

export const listTestRecords = () =>
  fetch(`${BASE}/api/test_records`).then(r=>r.json())

export const createTestRecord = (p) =>
  fetch(`${BASE}/api/test_records`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(p)
  }).then(r=>r.json())

export const getConstructionData = () =>
  fetch(`${BASE}/api/construction/geojson`).then(r=>r.json())

export const updateConstructionData = () =>
  fetch(`${BASE}/api/construction/update`).then(r=>r.json())

export const getConstructionNotices = (skip = 0, limit = 100) =>
  fetch(`${BASE}/api/construction/notices?skip=${skip}&limit=${limit}`).then(r=>r.json())

export const suggestRoadSegments = async (keyword, limit = 10) => {
  if (!keyword) return []
  const params = new URLSearchParams({ q: keyword, limit: String(limit) })
  const res = await fetch(`${BASE}/api/road_segments/suggest?${params.toString()}`)
  if (!res.ok) throw new Error('Failed to fetch road segment suggestions')
  const data = await res.json()
  return Array.isArray(data?.items) ? data.items : []
}

export const fetchRoadSegmentsByName = async (name) => {
  if (!name) return null
  const params = new URLSearchParams({ name })
  const res = await fetch(`${BASE}/api/road_segments/search?${params.toString()}`)
  if (!res.ok) throw new Error('Failed to fetch road segments')
  return res.json()
}
