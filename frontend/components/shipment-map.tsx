"use client"

import { useState, useCallback, useRef, useMemo, memo } from "react"
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  Line,
  ZoomableGroup,
} from "react-simple-maps"
import { geoCentroid } from "d3-geo"
import type { Shipment } from "@/lib/types"
import { cn } from "@/lib/utils"

// ── Data Sources ──────────────────────────────────────────────────────────────
const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
const INDIA_STATES_URL =
  "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"

// ── Shipment city coordinates [lon, lat] ─────────────────────────────────────
const CITY_COORDS: Record<string, [number, number]> = {
  Mumbai: [72.8777, 19.076], Delhi: [77.1025, 28.7041],
  Bangalore: [77.5946, 12.9716], Chennai: [80.2707, 13.0827],
  Kolkata: [88.3639, 22.5726], Hyderabad: [78.4867, 17.385],
  Pune: [73.8567, 18.5204], Ahmedabad: [72.5714, 23.0225],
  Jaipur: [75.7873, 26.9124], Lucknow: [80.9462, 26.8467],
  Singapore: [103.8198, 1.3521], Dubai: [55.2708, 25.2048],
  Shanghai: [121.4737, 31.2304], London: [-0.1278, 51.5074],
  "New York": [-74.006, 40.7128], Tokyo: [139.6917, 35.6895],
  Sydney: [151.2093, -33.8688], "Los Angeles": [-118.2437, 34.0522],
  Hamburg: [9.9937, 53.5511], Rotterdam: [4.4777, 51.9244],
}

// ── Indian state capitals [lon, lat] ─────────────────────────────────────────
const INDIA_STATE_CAPITALS: Record<string, [number, number]> = {
  Maharashtra: [72.8777, 19.076], "Uttar Pradesh": [80.9462, 26.8467],
  Karnataka: [77.5946, 12.9716], "Tamil Nadu": [80.2707, 13.0827],
  "West Bengal": [88.3639, 22.5726], Telangana: [78.4867, 17.385],
  Gujarat: [72.5714, 23.0225], Rajasthan: [75.7873, 26.9124],
  "Madhya Pradesh": [77.4126, 23.2599], Bihar: [85.1376, 25.6093],
  "Andhra Pradesh": [80.6480, 16.5062], Punjab: [75.8573, 30.7333],
  Haryana: [76.0856, 29.0588], Jharkhand: [85.3096, 23.3441],
  Odisha: [85.8245, 20.9517], Kerala: [76.2711, 10.8505],
  Chhattisgarh: [81.6296, 21.2514], Assam: [91.7362, 26.1445],
  Uttarakhand: [79.0193, 30.0668], Goa: [74.1240, 15.2993],
  Himachal: [77.1734, 31.1048],
}

// ── Extra Indian cities (appear at deep zoom) [lon, lat] ─────────────────────
const INDIA_CITIES: { name: string; coords: [number, number]; tier: number }[] = [
  // Tier 1 — show at zoom ≥ 4
  { name: "Mumbai", coords: [72.8777, 19.076], tier: 1 },
  { name: "Delhi", coords: [77.1025, 28.7041], tier: 1 },
  { name: "Bangalore", coords: [77.5946, 12.9716], tier: 1 },
  { name: "Hyderabad", coords: [78.4867, 17.385], tier: 1 },
  { name: "Chennai", coords: [80.2707, 13.0827], tier: 1 },
  { name: "Kolkata", coords: [88.3639, 22.5726], tier: 1 },
  { name: "Ahmedabad", coords: [72.5714, 23.0225], tier: 1 },
  { name: "Pune", coords: [73.8567, 18.5204], tier: 1 },
  // Tier 2 — show at zoom ≥ 6
  { name: "Jaipur", coords: [75.7873, 26.9124], tier: 2 },
  { name: "Lucknow", coords: [80.9462, 26.8467], tier: 2 },
  { name: "Surat", coords: [72.8311, 21.1702], tier: 2 },
  { name: "Nagpur", coords: [79.0882, 21.1458], tier: 2 },
  { name: "Patna", coords: [85.1376, 25.6093], tier: 2 },
  { name: "Indore", coords: [75.8577, 22.7196], tier: 2 },
  { name: "Bhopal", coords: [77.4126, 23.2599], tier: 2 },
  { name: "Kochi", coords: [76.2673, 9.9312], tier: 2 },
  { name: "Coimbatore", coords: [76.9558, 11.0168], tier: 2 },
  { name: "Visakhapatnam", coords: [83.2185, 17.6868], tier: 2 },
  { name: "Chandigarh", coords: [76.7794, 30.7333], tier: 2 },
  { name: "Bhubaneswar", coords: [85.8245, 20.2961], tier: 2 },
  // Tier 3 — show at zoom ≥ 9
  { name: "Vadodara", coords: [73.1812, 22.3072], tier: 3 },
  { name: "Agra", coords: [78.0081, 27.1767], tier: 3 },
  { name: "Varanasi", coords: [82.9913, 25.3176], tier: 3 },
  { name: "Madurai", coords: [78.1198, 9.9252], tier: 3 },
  { name: "Rajkot", coords: [70.8022, 22.3039], tier: 3 },
  { name: "Ranchi", coords: [85.3096, 23.3441], tier: 3 },
  { name: "Guwahati", coords: [91.7362, 26.1445], tier: 3 },
  { name: "Thiruvananthapuram", coords: [76.9366, 8.5241], tier: 3 },
  { name: "Mysore", coords: [76.6394, 12.2958], tier: 3 },
  { name: "Dehradun", coords: [78.0322, 30.3165], tier: 3 },
  { name: "Raipur", coords: [81.6296, 21.2514], tier: 3 },
  { name: "Jodhpur", coords: [73.0243, 26.2389], tier: 3 },
  { name: "Amritsar", coords: [74.8723, 31.6340], tier: 3 },
  { name: "Nashik", coords: [73.7898, 20.0063], tier: 3 },
  { name: "Aurangabad", coords: [75.3433, 19.8762], tier: 3 },
  { name: "Mangalore", coords: [74.8560, 12.9141], tier: 3 },
  { name: "Gwalior", coords: [78.1828, 26.2183], tier: 3 },
  { name: "Jabalpur", coords: [79.9864, 23.1815], tier: 3 },
]

// ── Global cities (non-India, for mid-zoom) ──────────────────────────────────
const GLOBAL_CITIES: { name: string; coords: [number, number]; tier: number }[] = [
  { name: "London", coords: [-0.1278, 51.5074], tier: 1 },
  { name: "New York", coords: [-74.006, 40.7128], tier: 1 },
  { name: "Tokyo", coords: [139.6917, 35.6895], tier: 1 },
  { name: "Shanghai", coords: [121.4737, 31.2304], tier: 1 },
  { name: "Dubai", coords: [55.2708, 25.2048], tier: 1 },
  { name: "Singapore", coords: [103.8198, 1.3521], tier: 1 },
  { name: "Sydney", coords: [151.2093, -33.8688], tier: 2 },
  { name: "Los Angeles", coords: [-118.2437, 34.0522], tier: 2 },
  { name: "Hamburg", coords: [9.9937, 53.5511], tier: 2 },
  { name: "Rotterdam", coords: [4.4777, 51.9244], tier: 2 },
  { name: "Paris", coords: [2.3522, 48.8566], tier: 2 },
  { name: "Beijing", coords: [116.4074, 39.9042], tier: 2 },
  { name: "Seoul", coords: [126.978, 37.5665], tier: 2 },
  { name: "Bangkok", coords: [100.5018, 13.7563], tier: 2 },
  { name: "Cairo", coords: [31.2357, 30.0444], tier: 2 },
  { name: "São Paulo", coords: [-46.6333, -23.5505], tier: 2 },
]

// ── Country label config ─────────────────────────────────────────────────────
const MAJOR_COUNTRIES = new Set([
  "Russia", "China", "United States of America", "India", "Brazil",
  "Canada", "Australia", "Argentina", "Saudi Arabia", "Indonesia",
  "Kazakhstan", "Algeria", "Mongolia", "Iran", "Mexico",
  "Libya", "Sudan", "Egypt", "South Africa", "Turkey",
  "France", "Germany", "Spain", "United Kingdom", "Italy",
  "Japan", "Pakistan", "Nigeria", "Colombia", "Ethiopia",
  "Peru", "Angola", "Mali", "Niger", "Chad", "Greenland",
])
const SKIP_LABELS = new Set([
  "Antarctica", "Fr. S. Antarctic Lands", "Heard I. and McDonald Is.",
  "Falkland Is.", "S. Geo. and the Is.",
])

// ── Helpers ──────────────────────────────────────────────────────────────────
function getRouteColor(delayRisk: number): string {
  if (delayRisk >= 0.7) return "#ef4444"
  if (delayRisk >= 0.4) return "#f59e0b"
  return "#22c55e"
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "in_transit": return "In Transit"
    case "at_risk": return "At Risk"
    case "delayed": return "Delayed"
    case "dispatched": return "Dispatched"
    case "delivered": return "Delivered"
    default: return status
  }
}

// Check if a coordinate is roughly inside the Indian bounding box
function isNearIndia(coords: [number, number]): boolean {
  const [lon, lat] = coords
  return lon >= 68 && lon <= 97 && lat >= 6 && lat <= 37
}

// ── Zoom level thresholds (Google Maps style) ────────────────────────────────
// 1.0–1.8  : World — countries only, no labels
// 1.8–3.5  : Country labels appear (major first)
// 3.5–5.0  : India states boundaries + state names, tier-1 global cities
// 5.0–8.0  : Indian tier-1 cities, tier-2 global cities
// 8.0–12   : Indian tier-2 cities, state capitals bold
// 12+      : Indian tier-3 cities (all)

interface ShipmentMapProps {
  shipments: Shipment[]
}

function ShipmentMapInner({ shipments }: ShipmentMapProps) {
  const [hoveredShipment, setHoveredShipment] = useState<Shipment | null>(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })
  const [position, setPosition] = useState<{ coordinates: [number, number]; zoom: number }>({
    coordinates: [0, 20],
    zoom: 1,
  })
  const mapRef = useRef<HTMLDivElement>(null)

  const handleMoveEnd = useCallback((pos: { coordinates: [number, number]; zoom: number }) => {
    setPosition(pos)
  }, [])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setPosition((prev) => {
      const factor = e.deltaY < 0 ? 1.18 : 1 / 1.18
      const newZoom = Math.min(Math.max(prev.zoom * factor, 1), 20)
      return { ...prev, zoom: newZoom }
    })
  }, [])

  const handleZoomIn = useCallback(() => {
    setPosition((p) => ({ ...p, zoom: Math.min(p.zoom * 1.5, 20) }))
  }, [])
  const handleZoomOut = useCallback(() => {
    setPosition((p) => ({ ...p, zoom: Math.max(p.zoom / 1.5, 1) }))
  }, [])
  const handleReset = useCallback(() => {
    setPosition({ coordinates: [0, 20], zoom: 1 })
  }, [])

  const zoom = position.zoom

  // Shipment routes and active cities
  const { routeData, activeCities } = useMemo(() => {
    const citySet = new Set<string>()
    const routes: { shipment: Shipment; from: [number, number]; to: [number, number] }[] = []
    shipments.forEach((s) => {
      const from = CITY_COORDS[s.origin]
      const to = CITY_COORDS[s.destination]
      if (from && to) {
        citySet.add(s.origin)
        citySet.add(s.destination)
        routes.push({ shipment: s, from, to })
      }
    })
    return {
      routeData: routes,
      activeCities: Array.from(citySet).map((name) => ({ name, coords: CITY_COORDS[name] })),
    }
  }, [shipments])

  // Zoom-dependent scale factors
  const inv = 1 / zoom
  const countryLabelSize = Math.max(2, 4 * inv)
  const stateLabelSize = Math.max(1.5, 3 * inv)
  const cityLabelSize = Math.max(2, 5 * inv)
  const cityDotR = Math.max(1, 2.5 * inv)
  const shipmentDotR = Math.max(1.5, 3 * inv)
  const shipmentLabelSize = Math.max(3, 6 * inv)

  // Progressive visibility
  const showCountryLabels = zoom >= 1.8
  const showMinorCountryLabels = zoom >= 3
  const showIndiaStates = zoom >= 3.5
  const showStateLabels = zoom >= 4
  const showIndiaCities = zoom >= 5
  const isViewingIndia = isNearIndia(position.coordinates) && zoom >= 3.5

  // Which India city tiers to show
  const indiaCityTier = zoom >= 12 ? 3 : zoom >= 8 ? 2 : zoom >= 5 ? 1 : 0
  // Global city tiers
  const globalCityTier = zoom >= 5 ? 2 : zoom >= 3.5 ? 1 : 0

  // Visible geographic cities (non-shipment)
  const geoCities = useMemo(() => {
    const result: { name: string; coords: [number, number]; size: "lg" | "md" | "sm" }[] = []
    if (indiaCityTier > 0) {
      INDIA_CITIES.forEach((c) => {
        if (c.tier <= indiaCityTier) {
          result.push({
            name: c.name,
            coords: c.coords,
            size: c.tier === 1 ? "lg" : c.tier === 2 ? "md" : "sm",
          })
        }
      })
    }
    if (globalCityTier > 0) {
      GLOBAL_CITIES.forEach((c) => {
        if (c.tier <= globalCityTier) {
          result.push({
            name: c.name,
            coords: c.coords,
            size: c.tier === 1 ? "lg" : "md",
          })
        }
      })
    }
    return result
  }, [indiaCityTier, globalCityTier])

  // Current zoom level indicator
  const zoomLabel =
    zoom < 1.8 ? "World" :
    zoom < 3.5 ? "Countries" :
    zoom < 5 ? "States" :
    zoom < 8 ? "Cities" : "Detail"

  return (
    <div ref={mapRef} className="relative w-full" onWheel={handleWheel}>
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ scale: 150, center: [0, 20] }}
        style={{ width: "100%", height: "auto" }}
        viewBox="0 0 800 450"
      >
        <ZoomableGroup
          center={position.coordinates}
          zoom={zoom}
          onMoveEnd={handleMoveEnd}
          minZoom={1}
          maxZoom={20}
          translateExtent={[[-200, -200], [1000, 650]]}
        >
          {/* Layer 1: World countries */}
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rpiKey ?? geo.properties?.name ?? geo.id}
                  geography={geo}
                  fill="hsl(240, 4%, 10%)"
                  stroke="hsl(240, 3.7%, 20%)"
                  strokeWidth={0.5 * inv}
                  style={{
                    default: { outline: "none" },
                    hover: { fill: "hsl(240, 4%, 14%)", outline: "none" },
                    pressed: { outline: "none" },
                  }}
                />
              ))
            }
          </Geographies>

          {/* Layer 2: India state boundaries (zoom ≥ 3.5) */}
          {showIndiaStates && (
            <Geographies geography={INDIA_STATES_URL}>
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rpiKey ?? geo.properties?.st_nm ?? geo.id}
                    geography={geo}
                    fill="transparent"
                    stroke="hsl(200, 50%, 25%)"
                    strokeWidth={0.3 * inv}
                    style={{
                      default: { outline: "none" },
                      hover: { fill: "hsl(200, 50%, 12%)", outline: "none" },
                      pressed: { outline: "none" },
                    }}
                  />
                ))
              }
            </Geographies>
          )}

          {/* Layer 3: Country name labels */}
          {showCountryLabels && (
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies
                  .filter((geo) => {
                    const name: string = geo.properties?.name ?? ""
                    if (!name || SKIP_LABELS.has(name)) return false
                    return MAJOR_COUNTRIES.has(name) || showMinorCountryLabels
                  })
                  .map((geo) => {
                    const centroid = geoCentroid(geo) as [number, number]
                    const name: string = geo.properties?.name ?? ""
                    if (centroid[0] === 0 && centroid[1] === 0) return null
                    return (
                      <Marker key={`ctry-${name}`} coordinates={centroid}>
                        <text
                          textAnchor="middle"
                          alignmentBaseline="central"
                          style={{
                            fontFamily: "Inter, sans-serif",
                            fontSize: `${countryLabelSize}px`,
                            fill: MAJOR_COUNTRIES.has(name)
                              ? "hsl(240, 5%, 38%)"
                              : "hsl(240, 3%, 28%)",
                            fontWeight: MAJOR_COUNTRIES.has(name) ? 600 : 400,
                            pointerEvents: "none",
                            userSelect: "none",
                            textTransform: "uppercase",
                            letterSpacing: "0.5px",
                          }}
                        >
                          {name}
                        </text>
                      </Marker>
                    )
                  })
              }
            </Geographies>
          )}

          {/* Layer 4: India state name labels (zoom ≥ 4) */}
          {showStateLabels && (
            <Geographies geography={INDIA_STATES_URL}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const centroid = geoCentroid(geo) as [number, number]
                  const name: string = geo.properties?.st_nm ?? ""
                  if (!name || (centroid[0] === 0 && centroid[1] === 0)) return null
                  return (
                    <Marker key={`state-${name}`} coordinates={centroid}>
                      <text
                        textAnchor="middle"
                        alignmentBaseline="central"
                        style={{
                          fontFamily: "Inter, sans-serif",
                          fontSize: `${stateLabelSize}px`,
                          fill: "hsl(200, 40%, 50%)",
                          fontWeight: 500,
                          pointerEvents: "none",
                          userSelect: "none",
                        }}
                      >
                        {name}
                      </text>
                    </Marker>
                  )
                })
              }
            </Geographies>
          )}

          {/* Layer 5: Geographic city dots (non-shipment) */}
          {geoCities.map((city) => {
            const r = city.size === "lg" ? cityDotR * 1.2 : city.size === "md" ? cityDotR : cityDotR * 0.7
            return (
              <Marker key={`geo-${city.name}`} coordinates={city.coords}>
                <circle
                  r={r}
                  fill="hsl(220, 15%, 45%)"
                  stroke="hsl(0, 0%, 5%)"
                  strokeWidth={0.5 * inv}
                />
                <text
                  textAnchor="middle"
                  y={-(r + cityLabelSize * 0.6)}
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: `${city.size === "lg" ? cityLabelSize : cityLabelSize * 0.85}px`,
                    fill: "hsl(220, 10%, 55%)",
                    fontWeight: city.size === "lg" ? 500 : 400,
                    pointerEvents: "none",
                    userSelect: "none",
                  }}
                >
                  {city.name}
                </text>
              </Marker>
            )
          })}

          {/* Layer 6: Shipment route arcs */}
          {routeData.map(({ shipment, from, to }) => (
            <Line
              key={shipment.shipment_id}
              from={from}
              to={to}
              stroke={getRouteColor(shipment.delay_risk)}
              strokeWidth={(shipment.delay_risk >= 0.7 ? 2 : 1.5) * inv}
              strokeLinecap="round"
              strokeDasharray={
                shipment.status === "in_transit" ? "6 4" :
                shipment.status === "delayed" ? "4 3" : undefined
              }
              style={{
                opacity: hoveredShipment?.shipment_id === shipment.shipment_id ? 1 : 0.6,
              }}
              className={shipment.status === "in_transit" ? "animate-dash" : ""}
              onMouseEnter={(evt: React.MouseEvent) => {
                setHoveredShipment(shipment)
                setTooltipPos({ x: evt.clientX, y: evt.clientY })
              }}
              onMouseLeave={() => setHoveredShipment(null)}
            />
          ))}

          {/* Layer 7: Shipment city markers (always visible) */}
          {activeCities.map((city) => {
            const hasIssue = shipments.some(
              (s) =>
                (s.origin === city.name || s.destination === city.name) &&
                (s.status === "at_risk" || s.status === "delayed" || s.delay_risk >= 0.7)
            )
            return (
              <Marker key={`ship-${city.name}`} coordinates={city.coords}>
                {hasIssue && (
                  <circle r={8 * inv} fill="none" stroke="#ef4444" strokeWidth={1 * inv} opacity={0.4}>
                    <animate attributeName="r" from={`${4 * inv}`} to={`${12 * inv}`} dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" from="0.6" to="0" dur="2s" repeatCount="indefinite" />
                  </circle>
                )}
                <circle
                  r={hasIssue ? shipmentDotR * 1.3 : shipmentDotR}
                  fill={hasIssue ? "#ef4444" : "hsl(199, 89%, 48%)"}
                  stroke="hsl(0, 0%, 3.9%)"
                  strokeWidth={1.5 * inv}
                />
                <text
                  textAnchor="middle"
                  y={-shipmentLabelSize * 1.5}
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: `${shipmentLabelSize}px`,
                    fill: hasIssue ? "#fca5a5" : "#a1a1aa",
                    fontWeight: hasIssue ? 600 : 400,
                    pointerEvents: "none",
                  }}
                >
                  {city.name}
                </text>
              </Marker>
            )
          })}
        </ZoomableGroup>
      </ComposableMap>

      {/* Zoom Controls */}
      <div className="absolute top-3 right-3 flex flex-col gap-1">
        <button onClick={handleZoomIn} className="h-7 w-7 rounded bg-black/60 backdrop-blur border border-white/[0.08] text-foreground text-sm font-bold hover:bg-white/[0.08] transition-colors flex items-center justify-center">+</button>
        <button onClick={handleZoomOut} className="h-7 w-7 rounded bg-black/60 backdrop-blur border border-white/[0.08] text-foreground text-sm font-bold hover:bg-white/[0.08] transition-colors flex items-center justify-center">−</button>
        <button onClick={handleReset} className="h-7 w-7 rounded bg-black/60 backdrop-blur border border-white/[0.08] text-muted-foreground text-[9px] font-bold hover:bg-white/[0.08] transition-colors flex items-center justify-center" title="Reset zoom">⟲</button>
      </div>

      {/* Zoom level badge */}
      <div className="absolute top-3 left-3 px-2 py-0.5 rounded bg-black/60 backdrop-blur border border-white/[0.08] text-[10px] text-muted-foreground select-none">
        {zoom.toFixed(1)}× · {zoomLabel}
      </div>

      {/* Tooltip */}
      {hoveredShipment && (
        <div
          className="fixed z-[9999] pointer-events-none px-3 py-2 rounded-lg border border-border bg-card text-card-foreground shadow-xl"
          style={{ left: tooltipPos.x + 12, top: tooltipPos.y - 40 }}
        >
          <p className="text-xs font-semibold">{hoveredShipment.shipment_id}</p>
          <p className="text-[10px] text-muted-foreground">
            {hoveredShipment.origin} → {hoveredShipment.destination}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span
              className={cn(
                "text-[10px] font-medium px-1.5 py-0.5 rounded",
                hoveredShipment.delay_risk >= 0.7
                  ? "bg-red-500/20 text-red-400"
                  : hoveredShipment.delay_risk >= 0.4
                  ? "bg-amber-500/20 text-amber-400"
                  : "bg-emerald-500/20 text-emerald-400"
              )}
            >
              Risk: {Math.round(hoveredShipment.delay_risk * 100)}%
            </span>
            <span className="text-[10px] text-muted-foreground">
              {getStatusLabel(hoveredShipment.status)}
            </span>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-2 left-3 flex items-center gap-4 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-5 rounded-full bg-emerald-500" /> Low Risk
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-5 rounded-full bg-amber-500" /> Medium Risk
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-5 rounded-full bg-red-500" /> High Risk
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" /> Issue Detected
        </span>
      </div>
    </div>
  )
}

const ShipmentMap = memo(ShipmentMapInner)
export default ShipmentMap
