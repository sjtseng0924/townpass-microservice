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

// Favorite APIs
export const getFavorites = async (externalId) => {
  if (!externalId) throw new Error('External User ID is required')
  const params = new URLSearchParams({ external_id: externalId })
  const res = await fetch(`${BASE}/api/favorites?${params.toString()}`)
  if (!res.ok) throw new Error('Failed to fetch favorites')
  return res.json()
}

export const createFavorite = async (favoriteData, externalId) => {
  if (!externalId) throw new Error('External User ID is required')
  // 移除 user_id，使用 external_id 查詢參數
  const { user_id, ...dataWithoutUserId } = favoriteData
  const params = new URLSearchParams({ external_id: externalId })
  const res = await fetch(`${BASE}/api/favorites?${params.toString()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dataWithoutUserId)
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to create favorite' }))
    throw new Error(error.detail || 'Failed to create favorite')
  }
  return res.json()
}

export const updateFavorite = async (favoriteId, externalId, updateData) => {
  if (!favoriteId || !externalId) throw new Error('Favorite ID and External User ID are required')
  const params = new URLSearchParams({ external_id: externalId })
  const res = await fetch(`${BASE}/api/favorites/${favoriteId}?${params.toString()}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updateData)
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to update favorite' }))
    throw new Error(error.detail || 'Failed to update favorite')
  }
  return res.json()
}

export const deleteFavorite = async (favoriteId, externalId) => {
  if (!favoriteId || !externalId) throw new Error('Favorite ID and External User ID are required')
  const params = new URLSearchParams({ external_id: externalId })
  const res = await fetch(`${BASE}/api/favorites/${favoriteId}?${params.toString()}`, {
    method: 'DELETE'
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to delete favorite' }))
    throw new Error(error.detail || 'Failed to delete favorite')
  }
  return res.json()
}