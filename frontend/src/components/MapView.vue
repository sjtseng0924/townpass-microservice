<script setup>
import { onMounted, onBeforeUnmount, ref, createApp } from 'vue'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import MapPopup from './map/MapPopup.vue'

const mapEl = ref(null)
let map = null

// Datasets to toggle
const datasets = ref([
  { id: 'accessibility', name: '無障礙據點', url: '/mapData/accessibility_new_tpe.geojson', color: '#10b981', outline: '#064e3b', visible: true },
  { id: 'attraction', name: '景點', url: '/mapData/attraction_tpe.geojson', color: '#f59e0b', outline: '#92400e', visible: false },
])

const datasetCache = new Map()

function computeBounds(geo) {
  const bounds = new mapboxgl.LngLatBounds()
  for (const f of geo.features || []) {
    const g = f.geometry
    if (!g) continue
    if (g.type === 'Point') bounds.extend(g.coordinates)
    else if (g.type === 'MultiPoint' || g.type === 'LineString') for (const c of g.coordinates) bounds.extend(c)
    else if (g.type === 'MultiLineString' || g.type === 'Polygon') for (const ring of g.coordinates) for (const c of ring) bounds.extend(c)
    else if (g.type === 'MultiPolygon') for (const poly of g.coordinates) for (const ring of poly) for (const c of ring) bounds.extend(c)
  }
  return bounds
}

function attachPopupInteraction(layerId) {
  map.on('mouseenter', layerId, () => { map.getCanvas().style.cursor = 'pointer' })
  map.on('mouseleave', layerId, () => { map.getCanvas().style.cursor = '' })
  map.on('click', layerId, (e) => {
    const feature = e?.features?.[0]
    if (!feature) return
    const props = feature.properties || {}
    const container = document.createElement('div')
    const app = createApp(MapPopup, { properties: props })
    app.mount(container)
    const popup = new mapboxgl.Popup({ offset: 8 })
      .setLngLat(e.lngLat)
      .setDOMContent(container)
      .addTo(map)
    popup.on('close', () => app.unmount())
  })
}

async function ensureDatasetLoaded(ds) {
  if (!map || datasetCache.has(ds.id)) return
  const geo = await fetch(ds.url).then(r => r.json())
  const sourceId = `geo-${ds.id}`
  const first = geo?.features?.[0]
  const geomType = first?.geometry?.type || ''
  map.addSource(sourceId, { type: 'geojson', data: geo })
  const layerIds = []
  if (geomType.includes('Point')) {
    const lid = `${ds.id}-points`
    map.addLayer({ id: lid, type: 'circle', source: sourceId, paint: { 'circle-radius': 6, 'circle-color': ds.color || '#3b82f6', 'circle-stroke-width': 1, 'circle-stroke-color': ds.outline || '#1d4ed8' }, layout: { visibility: ds.visible ? 'visible' : 'none' } })
    layerIds.push(lid)
    attachPopupInteraction(lid)
  } else if (geomType.includes('Line')) {
    const lid = `${ds.id}-lines`
    map.addLayer({ id: lid, type: 'line', source: sourceId, paint: { 'line-color': ds.color || '#0ea5e9', 'line-width': 2 }, layout: { visibility: ds.visible ? 'visible' : 'none' } })
    layerIds.push(lid)
    attachPopupInteraction(lid)
  } else {
    const fillId = `${ds.id}-fill`
    const outlineId = `${ds.id}-outline`
    map.addLayer({ id: fillId, type: 'fill', source: sourceId, paint: { 'fill-color': ds.color || '#3b82f6', 'fill-opacity': 0.2 }, layout: { visibility: ds.visible ? 'visible' : 'none' } })
    map.addLayer({ id: outlineId, type: 'line', source: sourceId, paint: { 'line-color': ds.outline || '#1d4ed8', 'line-width': 1 }, layout: { visibility: ds.visible ? 'visible' : 'none' } })
    layerIds.push(fillId, outlineId)
    attachPopupInteraction(fillId)
  }
  datasetCache.set(ds.id, { sourceId, layerIds, geo, bounds: computeBounds(geo) })
}

function setDatasetVisibility(ds, visible) {
  const cache = datasetCache.get(ds.id)
  if (!cache) return
  for (const lid of cache.layerIds) if (map.getLayer(lid)) map.setLayoutProperty(lid, 'visibility', visible ? 'visible' : 'none')
}

function fitToVisibleDatasets() {
  const visible = datasets.value.map(d => d.visible ? datasetCache.get(d.id) : null).filter(Boolean)
  if (visible.length === 0) return
  const combined = new mapboxgl.LngLatBounds()
  for (const c of visible) if (c.bounds && !c.bounds.isEmpty()) { combined.extend(c.bounds.getSouthWest()); combined.extend(c.bounds.getNorthEast()) }
  if (!combined.isEmpty()) map.fitBounds(combined, { padding: 40, duration: 500 })
}

onMounted(() => {
  const token = import.meta.env.VITE_MAPBOXTOKEN
  const rawStyle = import.meta.env.VITE_MAPBOXTILE

  let styleUrl = 'mapbox://styles/mapbox/streets-v12'
  if (rawStyle) {
    const v = String(rawStyle).trim()
    if (v.startsWith('mapbox://') || v.startsWith('http')) {
      styleUrl = v
    } else if (v.includes('/')) {
      styleUrl = `mapbox://styles/${v}`
    } else if (v.includes('.')) {
      // allow tileset-like "user.styleid" to be used as style "user/styleid"
      const normalized = v.replace('.', '/')
      styleUrl = `mapbox://styles/${normalized}`
    }
  }

  if (!token) {
    console.warn('VITE_MAPBOXTOKEN is missing')
    return
  }

  mapboxgl.accessToken = token
  map = new mapboxgl.Map({
    container: mapEl.value,
    style: styleUrl,
    center: [121.5654, 25.0330],
    zoom: 11
  })

  map.addControl(new mapboxgl.NavigationControl())

  map.on('error', (e) => {
    console.warn('Mapbox error:', e?.error || e)
  })

  map.on('load', async () => {
    try {
      for (const ds of datasets.value) await ensureDatasetLoaded(ds)
      fitToVisibleDatasets()
    } catch (err) {
      console.warn('Failed to load datasets:', err)
    }
  })
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <section class="h-full flex flex-col">
    <div class="flex items-center gap-3 py-2">
      <h1 class="text-2xl font-semibold">地圖</h1>
      <div class="flex items-center gap-3 flex-wrap">
        <label v-for="ds in datasets" :key="ds.id" class="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" v-model="ds.visible" @change="() => { setDatasetVisibility(ds, ds.visible); fitToVisibleDatasets() }" />
          <span>{{ ds.name }}</span>
        </label>
      </div>
    </div>
    <div ref="mapEl" class="flex-1 min-h-[400px]" />
  </section>
  
  
</template>

<style scoped>
</style>


