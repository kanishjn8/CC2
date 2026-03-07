"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardTitle } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { Button } from "@/components/ui/button"

interface ShipmentData {
  Date: string
  "Flight No.": string // Database field, represents Shipment ID
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

interface ShipmentTonnageStackedChartProps {
  data: ShipmentData[]
}

// Color palette for routes
const ROUTE_COLORS = [
  "#06b6d4", // cyan-500
  "#8b5cf6", // violet-500
  "#f59e0b", // amber-500
  "#10b981", // emerald-500
  "#ef4444", // red-500
  "#3b82f6", // blue-500
  "#ec4899", // pink-500
  "#14b8a6", // teal-500
]

export default function ShipmentTonnageStackedChart({ data }: ShipmentTonnageStackedChartProps) {
  const [viewMode, setViewMode] = useState<"Month" | "Day" | "Week">("Month")

  // Group data by month, day, or week based on viewMode
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    // Group by time period and route
    const grouped: Record<
      string,
      {
        [key: string]: number
        month?: string
        week?: string
        day?: string
      }
    > = {}

    data.forEach((item) => {
      if (!item.Date || !item.Dep || !item.Arr) return

      const date = new Date(item.Date)
      const route = `${item.Dep}-${item.Arr}`

      // Create key based on view mode
      let key: string
      let displayKey: string

      if (viewMode === "Month") {
        // Month view - use YYYY-MM format
        key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
        displayKey = date.toLocaleDateString("en-US", { month: "short", year: "numeric" })
      } else if (viewMode === "Week") {
        // Week view - use week start date
        const weekStart = new Date(date)
        weekStart.setDate(date.getDate() - date.getDay())
        key = `${weekStart.getFullYear()}-W${String(Math.ceil((weekStart.getDate() + weekStart.getDay()) / 7)).padStart(2, "0")}-${String(weekStart.getMonth() + 1).padStart(2, "0")}-${String(weekStart.getDate()).padStart(2, "0")}`
        displayKey = weekStart.toLocaleDateString("en-US", { month: "short", day: "numeric" })
      } else {
        // Day view - use full date
        key = item.Date.split("T")[0]
        displayKey = date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
      }

      if (!grouped[key]) {
        grouped[key] = {
          [viewMode === "Month" ? "month" : viewMode === "Week" ? "week" : "day"]: displayKey,
        }
      }

      if (!grouped[key][route]) {
        grouped[key][route] = 0
      }

      grouped[key][route] += item.KG || 0
    })

    // Convert to array and sort by date
    const result = Object.entries(grouped).map(([key, value]) => ({
      key,
      ...value,
    }))

    result.sort((a, b) => {
      const aKey = viewMode === "Month" ? a.month : viewMode === "Week" ? a.week : a.day
      const bKey = viewMode === "Month" ? b.month : viewMode === "Week" ? b.week : b.day
      return (aKey || "").localeCompare(bKey || "")
    })

    return result
  }, [data, viewMode])

  // Get all unique routes for the legend
  const routes = useMemo(() => {
    if (viewMode === "Month") {
      // For month view, show top 8 routes by total tonnage
      const routeTotals: Record<string, number> = {}

      data.forEach((item) => {
        if (!item.Dep || !item.Arr) return
        const route = `${item.Dep}-${item.Arr}`
        routeTotals[route] = (routeTotals[route] || 0) + (item.KG || 0)
      })

      return Object.entries(routeTotals)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 8)
        .map(([route]) => route)
    } else if (viewMode === "Week") {
      // For week view, show top 6 routes
      const routeTotals: Record<string, number> = {}

      data.forEach((item) => {
        if (!item.Dep || !item.Arr) return
        const route = `${item.Dep}-${item.Arr}`
        routeTotals[route] = (routeTotals[route] || 0) + (item.KG || 0)
      })

      return Object.entries(routeTotals)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 6)
        .map(([route]) => route)
    } else {
      // Day view
      const routeTotals: Record<string, number> = {}

      data.forEach((item) => {
        if (!item.Dep || !item.Arr) return
        const route = `${item.Dep}-${item.Arr}`
        routeTotals[route] = (routeTotals[route] || 0) + (item.KG || 0)
      })

      return Object.entries(routeTotals)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5)
        .map(([route]) => route)
    }
  }, [data, viewMode])

  return (
    <Card className="bg-card border-border shadow-xl">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-6">
          <CardTitle className="text-foreground">Shipment Tonnage by Routes</CardTitle>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={viewMode === "Month" ? "default" : "outline"}
              className={
                viewMode === "Month"
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "bg-transparent border-border text-muted-foreground hover:bg-accent hover:text-foreground"
              }
              onClick={() => setViewMode("Month")}
            >
              Month
            </Button>
            <Button
              size="sm"
              variant={viewMode === "Week" ? "default" : "outline"}
              className={
                viewMode === "Week"
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "bg-transparent border-border text-muted-foreground hover:bg-accent hover:text-foreground"
              }
              onClick={() => setViewMode("Week")}
            >
              Week
            </Button>
            <Button
              size="sm"
              variant={viewMode === "Day" ? "default" : "outline"}
              className={
                viewMode === "Day"
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "bg-transparent border-border text-muted-foreground hover:bg-accent hover:text-foreground"
              }
              onClick={() => setViewMode("Day")}
            >
              Day
            </Button>
          </div>
        </div>

        <p className="text-sm text-muted-foreground mb-4">
          {viewMode === "Month"
            ? "Monthly tonnage breakdown by top 8 routes"
            : viewMode === "Week"
              ? "Weekly tonnage breakdown by top 6 routes"
              : "Daily tonnage breakdown by top 5 routes"}
        </p>

        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={chartData}
            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: 5,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey={viewMode === "Month" ? "month" : viewMode === "Week" ? "week" : "day"}
              stroke="hsl(var(--muted-foreground))"
              tick={{ fill: "hsl(var(--muted-foreground))" }}
              angle={-45}
              textAnchor="end"
              height={80}
              interval={viewMode === "Day" ? "preserveStartEnd" : 0}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              tick={{ fill: "hsl(var(--muted-foreground))" }}
              label={{
                value: "Tonnage (kg)",
                angle: -90,
                position: "insideLeft",
                fill: "hsl(var(--muted-foreground))",
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                color: "hsl(var(--popover-foreground))",
              }}
              formatter={(value: number) => [`${value.toLocaleString()} kg`, ""]}
            />
            <Legend
              wrapperStyle={{
                paddingTop: "20px",
                color: "hsl(var(--foreground))",
              }}
            />
            {routes.map((route, index) => (
              <Bar key={route} dataKey={route} stackId="a" fill={ROUTE_COLORS[index % ROUTE_COLORS.length]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
