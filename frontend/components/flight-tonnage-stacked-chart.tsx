"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from "recharts"
import { BarChart3Icon, CalendarIcon } from "lucide-react"
import { format, startOfWeek, endOfWeek } from "date-fns"

interface FlightData {
  Date: string
  "Flight No.": string
  ACM: string
  KG: number
  Reg: string
  Month: string
  Year: number
  Day: string
  Sector: string
  Dep: string
  Arr: string
  "Out/In": string
  Station: string
  "Dom/Int": string
}

interface FlightTonnageStackedChartProps {
  data: FlightData[]
}

const COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--chart-6))",
  "hsl(var(--chart-7))",
  "hsl(var(--chart-8))",
  "hsl(var(--chart-9))",
  "hsl(var(--chart-10))",
]

export default function FlightTonnageStackedChart({ data }: FlightTonnageStackedChartProps) {
  const [viewMode, setViewMode] = useState<"Month" | "Day" | "Week">("Month")

  const { chartData, topRoutes } = useMemo(() => {
    // Get top routes by tonnage
    const routeTotals = data.reduce(
      (acc, item) => {
        if (!item.Dep || !item.Arr || !item.KG) return acc

        // Normalize route by trimming and removing all spaces
        const route = `${item.Dep.trim().replace(/\s+/g, "")}${item.Arr.trim().replace(/\s+/g, "")}`
        const tonnage = Number(item.KG) || 0

        if (!acc[route]) {
          acc[route] = 0
        }
        acc[route] += tonnage

        return acc
      },
      {} as Record<string, number>,
    )

    const topRoutes = Object.entries(routeTotals)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([route]) => route)

    // Group data by month, day, or week based on viewMode
    const groupedData = data.reduce(
      (acc, item) => {
        if (!item.Date || !item.KG || !item.Dep || !item.Arr) return acc

        const date = new Date(item.Date)
        // Normalize route by trimming and removing all spaces
        const route = `${item.Dep.trim().replace(/\s+/g, "")}${item.Arr.trim().replace(/\s+/g, "")}`
        const tonnage = Number(item.KG) || 0

        if (!topRoutes.includes(route)) return acc

        // Create key based on view mode
        let key: string
        let displayKey: string

        if (viewMode === "Month") {
          key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
          displayKey = key
        } else if (viewMode === "Week") {
          // Get the start of the week (Monday)
          const weekStart = startOfWeek(date, { weekStartsOn: 1 })
          const weekEnd = endOfWeek(date, { weekStartsOn: 1 })
          key = `${weekStart.getFullYear()}-W${String(Math.ceil((weekStart.getDate() + weekStart.getDay()) / 7)).padStart(2, "0")}-${String(weekStart.getMonth() + 1).padStart(2, "0")}-${String(weekStart.getDate()).padStart(2, "0")}`
          displayKey = key
        } else {
          // Day view - use full date
          key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`
          displayKey = key
        }

        if (!acc[key]) {
          acc[key] = {
            [viewMode === "Month" ? "month" : viewMode === "Week" ? "week" : "day"]: displayKey,
            total: 0,
          }
        }

        if (!acc[key][route]) {
          acc[key][route] = 0
        }

        acc[key][route] += tonnage
        acc[key].total += tonnage

        return acc
      },
      {} as Record<string, any>,
    )

    // Convert to array and sort by date - use all filtered data
    const chartData = Object.values(groupedData).sort((a: any, b: any) => {
      const aKey = viewMode === "Month" ? a.month : viewMode === "Week" ? a.week : a.day
      const bKey = viewMode === "Month" ? b.month : viewMode === "Week" ? b.week : b.day
      return aKey.localeCompare(bKey)
    })

    return { chartData, topRoutes }
  }, [data, viewMode])

  const formatDate = (dateKey: string) => {
    try {
      if (viewMode === "Month") {
        const [year, month] = dateKey.split("-")
        const date = new Date(Number(year), Number(month) - 1)
        return format(date, "MMM yyyy")
      } else if (viewMode === "Week") {
        // Parse week key format: YYYY-WXX-MM-DD
        const parts = dateKey.split("-")
        if (parts.length >= 4) {
          const year = Number(parts[0])
          const month = Number(parts[2]) - 1
          const day = Number(parts[3])
          const weekStart = new Date(year, month, day)
          const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 })
          return `${format(weekStart, "MMM d")} - ${format(weekEnd, "MMM d")}`
        }
        return dateKey
      } else {
        // Day view
        const [year, month, day] = dateKey.split("-")
        const date = new Date(Number(year), Number(month) - 1, Number(day))
        return format(date, "MMM d")
      }
    } catch {
      return dateKey
    }
  }

  const formatWeight = (kg: number) => {
    if (kg >= 1000000) {
      return `${(kg / 1000000).toFixed(1)}M kg`
    } else if (kg >= 1000) {
      return `${(kg / 1000).toFixed(1)}k kg`
    }
    return `${kg.toFixed(0)} kg`
  }

  return (
    <Card className="bg-card border-border shadow-xl">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-primary/10 rounded-md border border-primary/20">
              <BarChart3Icon className="h-5 w-5 text-primary" />
            </div>
            <CardTitle className="text-foreground">Flight Tonnage by Routes</CardTitle>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={viewMode === "Month" ? "default" : "outline"}
              className={`${
                viewMode === "Month"
                  ? "bg-primary text-primary-foreground"
                  : "bg-transparent border-border text-foreground hover:bg-accent"
              }`}
              onClick={() => setViewMode("Month")}
            >
              <CalendarIcon className="w-4 h-4 mr-1" />
              Month
            </Button>
            <Button
              size="sm"
              variant={viewMode === "Week" ? "default" : "outline"}
              className={`${
                viewMode === "Week"
                  ? "bg-primary text-primary-foreground"
                  : "bg-transparent border-border text-foreground hover:bg-accent"
              }`}
              onClick={() => setViewMode("Week")}
            >
              <CalendarIcon className="w-4 h-4 mr-1" />
              Week
            </Button>
            <Button
              size="sm"
              variant={viewMode === "Day" ? "default" : "outline"}
              className={`${
                viewMode === "Day"
                  ? "bg-primary text-primary-foreground"
                  : "bg-transparent border-border text-foreground hover:bg-accent"
              }`}
              onClick={() => setViewMode("Day")}
            >
              <CalendarIcon className="w-4 h-4 mr-1" />
              Day
            </Button>
          </div>
        </div>
        <p className="text-muted-foreground text-sm">
          {viewMode === "Month"
            ? "Monthly tonnage breakdown by top performing routes"
            : viewMode === "Week"
              ? "Weekly tonnage breakdown by top performing routes"
              : "Daily tonnage breakdown by top performing routes"}
        </p>
      </CardHeader>
      <CardContent>
        {/* Route Legend */}
        <div className="flex flex-wrap gap-2 mb-4">
          {topRoutes.map((route, index) => (
            <Badge
              key={route}
              variant="outline"
              className="text-xs border-border text-muted-foreground"
              style={{ borderColor: COLORS[index], color: COLORS[index] }}
            >
              {route}
            </Badge>
          ))}
        </div>

        {/* Stacked Bar Chart */}
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey={viewMode === "Month" ? "month" : viewMode === "Week" ? "week" : "day"}
                tickFormatter={formatDate}
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                angle={-45}
                textAnchor="end"
                height={80}
                interval={viewMode === "Day" ? "preserveStartEnd" : 0}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickFormatter={(value) => `${(value / 1000).toFixed(0)}t`}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload || !payload.length) return null

                  const total = payload.reduce((sum, entry) => sum + (entry.value || 0), 0)

                  return (
                    <div className="bg-popover border border-border rounded-lg p-4 shadow-xl min-w-[200px]">
                      <div className="text-foreground font-semibold text-lg mb-3 border-b border-border pb-2">
                        {formatDate(label)}
                      </div>
                      <div className="space-y-2">
                        {payload
                          .sort((a, b) => (b.value || 0) - (a.value || 0))
                          .map((entry, index) => (
                            <div key={index} className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
                                <span className="text-muted-foreground font-medium">{entry.dataKey}</span>
                              </div>
                              <span className="text-foreground font-semibold">{formatWeight(entry.value || 0)}</span>
                            </div>
                          ))}
                      </div>
                      <div className="mt-3 pt-2 border-t border-border">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Total:</span>
                          <span className="text-foreground font-bold">{formatWeight(total)}</span>
                        </div>
                      </div>
                    </div>
                  )
                }}
              />
              {topRoutes.map((route, index) => (
                <Bar key={route} dataKey={route} stackId="routes" fill={COLORS[index]} name={route} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
