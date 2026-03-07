"use client"

import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { PieChartIcon } from "lucide-react"

interface ShipmentData {
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

interface RouteDistributionChartProps {
  data: ShipmentData[]
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

export default function RouteDistributionChart({ data }: RouteDistributionChartProps) {
  const { chartData, totalTonnage, smallestRoute } = useMemo(() => {
    // Calculate route distribution
    const routeDistribution = data.reduce(
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

    const totalTonnage = Object.values(routeDistribution).reduce((sum, tonnage) => sum + tonnage, 0)

    // Get top 10 routes and format for pie chart
    const sortedRoutes = Object.entries(routeDistribution)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)

    const chartData = sortedRoutes.map(([route, tonnage], index) => ({
      name: route,
      value: tonnage,
      percentage: ((tonnage / totalTonnage) * 100).toFixed(1),
      fill: COLORS[index],
    }))

    // Identify the smallest route (10th position)
    const smallestRoute = sortedRoutes.length > 0 ? sortedRoutes[sortedRoutes.length - 1][0] : null

    return { chartData, totalTonnage, smallestRoute }
  }, [data])

  const formatWeight = (kg: number) => {
    if (kg >= 1000000) {
      return `${(kg / 1000000).toFixed(1)}M kg`
    } else if (kg >= 1000) {
      return `${(kg / 1000).toFixed(1)}k kg`
    }
    return `${kg.toFixed(0)} kg`
  }

  // Custom label function that positions the 10th (smallest) route at the top
  const renderCustomLabel = (entry: any) => {
    const { cx, cy, midAngle, innerRadius, outerRadius, name, percentage } = entry

    // Special positioning for the smallest route (10th position) - move to upper area
    if (name === smallestRoute) {
      // Position the smallest route in the upper area (around 12 o'clock position)
      const radius = outerRadius + 35
      const customAngle = -90 // 12 o'clock position (top)
      const baseX = cx + radius * Math.cos((customAngle * Math.PI) / 180)
      const baseY = cy + radius * Math.sin((customAngle * Math.PI) / 180)

      // Move 10% further away in both x and y directions
      const deltaX = (baseX - cx) * 0.1
      const deltaY = (baseY - cy) * 0.1
      const x = baseX + deltaX
      const y = baseY + deltaY

      return (
        <text
          x={x}
          y={y}
          fill={entry.fill}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize="14"
          fontWeight="500"
        >
          {`${name}: ${percentage}%`}
        </text>
      )
    }

    // Default positioning for all other labels with 10% additional distance
    const radius = outerRadius + 30
    const baseX = cx + radius * Math.cos((-midAngle * Math.PI) / 180)
    const baseY = cy + radius * Math.sin((-midAngle * Math.PI) / 180)

    // Move 10% further away in both x and y directions
    const deltaX = (baseX - cx) * 0.1
    const deltaY = (baseY - cy) * 0.1
    const x = baseX + deltaX
    const y = baseY + deltaY

    return (
      <text
        x={x}
        y={y}
        fill={entry.fill}
        textAnchor={x > cx ? "start" : "end"}
        dominantBaseline="central"
        fontSize="14"
        fontWeight="500"
      >
        {`${name}: ${percentage}%`}
      </text>
    )
  }

  return (
    <Card className="bg-card border-border shadow-xl">
      <CardHeader>
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-green-900/30 rounded-md border border-green-700/50">
            <PieChartIcon className="h-5 w-5 text-green-400" />
          </div>
          <div>
            <CardTitle className="text-foreground">Route Distribution</CardTitle>
            <p className="text-muted-foreground text-sm">Tonnage share by route (top 10)</p>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={120}
                paddingAngle={2}
                dataKey="value"
                label={renderCustomLabel}
                labelLine={false}
                startAngle={90}
                endAngle={450}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload || !payload.length) return null

                  const data = payload[0].payload
                  return (
                    <div className="bg-popover border border-border rounded-lg p-4 shadow-xl">
                      <div className="text-foreground font-semibold text-lg mb-2">{data.name}</div>
                      <div className="space-y-1">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Tonnage:</span>
                          <span className="text-foreground font-medium">{formatWeight(data.value)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Share:</span>
                          <span className="text-foreground font-medium">{data.percentage}%</span>
                        </div>
                      </div>
                    </div>
                  )
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
