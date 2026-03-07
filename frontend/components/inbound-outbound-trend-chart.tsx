"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { TrendingUp, Calendar } from "lucide-react"
import { format, parseISO, startOfWeek, endOfWeek } from "date-fns"
import { cn } from "@/lib/utils"

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

interface DateRangeInfo {
  from: string
  to: string
  isYTD: boolean
  recordCount: number
}

interface InboundOutboundTrendChartProps {
  data: ShipmentData[]
  dateRange: DateRangeInfo
}

type VisibleLines = {
  outbound: boolean
  inbound: boolean
  combined: boolean
}

export default function InboundOutboundTrendChart({ data, dateRange }: InboundOutboundTrendChartProps) {
  // State to track which lines are visible
  const [visibleLines, setVisibleLines] = useState<VisibleLines>({
    outbound: true,
    inbound: true,
    combined: true,
  })

  const chartData = useMemo(() => {
    // Group data by week and calculate inbound/outbound totals
    const weeklyData = data.reduce(
      (acc, item) => {
        // Skip if no date or KG data
        if (!item.Date || !item.KG || item.KG <= 0) return acc

        // Handle different date formats more robustly
        let dateStr: string
        try {
          const dateValue = item.Date
          if (typeof dateValue === "string") {
            // Extract just the date part, handle various formats
            if (dateValue.includes("T")) {
              dateStr = dateValue.split("T")[0]
            } else if (dateValue.includes(" ")) {
              dateStr = dateValue.split(" ")[0]
            } else {
              dateStr = dateValue
            }
          } else {
            dateStr = new Date(dateValue).toISOString().split("T")[0]
          }

          // Validate date format
          if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            return acc
          }
        } catch (error) {
          return acc
        }

        const date = parseISO(dateStr)
        const tonnage = Number(item.KG) || 0
        const direction = String(item["Out/In"] || "")
          .trim()
          .toUpperCase()

        // Get the start of the week (Monday as first day)
        const weekStart = startOfWeek(date, { weekStartsOn: 1 })
        const weekEnd = endOfWeek(date, { weekStartsOn: 1 })

        // Create a week key using the week start date
        const weekKey = format(weekStart, "yyyy-MM-dd")

        if (!acc[weekKey]) {
          acc[weekKey] = {
            date: weekKey,
            weekStart: weekStart,
            weekEnd: weekEnd,
            weekLabel: `${format(weekStart, "MMM d")} - ${format(weekEnd, "MMM d")}`,
            inbound: 0,
            outbound: 0,
            combined: 0,
          }
        }

        // Handle various possible values for direction
        if (direction === "IN" || direction === "INBOUND" || direction === "I") {
          acc[weekKey].inbound += tonnage
        } else if (direction === "OUT" || direction === "OUTBOUND" || direction === "O") {
          acc[weekKey].outbound += tonnage
        }

        acc[weekKey].combined += tonnage

        return acc
      },
      {} as Record<string, any>,
    )

    // Convert to array and sort by date
    return Object.values(weeklyData)
      .sort((a: any, b: any) => a.date.localeCompare(b.date))
      .map((item: any) => ({
        ...item,
        inbound: Math.round(item.inbound),
        outbound: Math.round(item.outbound),
        combined: Math.round(item.combined),
      }))
  }, [data])

  // Calculate summary statistics - FIXED to match dashboard logic exactly
  const summaryStats = useMemo(() => {
    // Use the SAME logic as the dashboard for consistency
    const totalTonnage = data.reduce((sum, item) => sum + (Number(item.KG) || 0), 0)

    // Filter data with proper null/undefined handling
    const outboundData = data.filter((item) => {
      const direction = String(item["Out/In"] || "")
        .trim()
        .toUpperCase()
      return direction === "OUT" || direction === "OUTBOUND" || direction === "O"
    })

    const inboundData = data.filter((item) => {
      const direction = String(item["Out/In"] || "")
        .trim()
        .toUpperCase()
      return direction === "IN" || direction === "INBOUND" || direction === "I"
    })

    // Calculate totals with proper number conversion
    const outboundTotal = outboundData.reduce((sum, item) => sum + (Number(item.KG) || 0), 0)
    const inboundTotal = inboundData.reduce((sum, item) => sum + (Number(item.KG) || 0), 0)

    const outboundShipments = outboundData.length
    const inboundShipments = inboundData.length

    // Calculate records with no direction or invalid direction
    const unclassifiedData = data.filter((item) => {
      const direction = String(item["Out/In"] || "")
        .trim()
        .toUpperCase()
      return !(
        direction === "OUT" ||
        direction === "OUTBOUND" ||
        direction === "O" ||
        direction === "IN" ||
        direction === "INBOUND" ||
        direction === "I"
      )
    })
    const unclassifiedTotal = unclassifiedData.reduce((sum, item) => sum + (Number(item.KG) || 0), 0)

    return {
      outbound: {
        total: outboundTotal,
        avg: outboundShipments > 0 ? outboundTotal / outboundShipments : 0,
        count: outboundShipments,
      },
      inbound: {
        total: inboundTotal,
        avg: inboundShipments > 0 ? inboundTotal / inboundShipments : 0,
        count: inboundShipments,
      },
      combined: {
        total: totalTonnage, // Use the same calculation as dashboard
        avg: data.length > 0 ? totalTonnage / data.length : 0,
        classified: outboundTotal + inboundTotal,
        unclassified: unclassifiedTotal,
      },
      debug: {
        totalRecords: data.length,
        outboundRecords: outboundShipments,
        inboundRecords: inboundShipments,
        unclassifiedRecords: unclassifiedData.length,
        totalFromDashboard: totalTonnage,
        classifiedTotal: outboundTotal + inboundTotal,
        unclassifiedTotal: unclassifiedTotal,
      },
    }
  }, [data])

  // Format the date range display
  const formatDateRange = () => {
    if (!dateRange.from || !dateRange.to) {
      return "All available data"
    }

    const fromDate = new Date(dateRange.from + "T00:00:00")
    const toDate = new Date(dateRange.to + "T00:00:00")

    if (dateRange.isYTD) {
      return `Year-to-Date: ${fromDate.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })} - ${toDate.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })}`
    }

    // Same year, show abbreviated format
    if (fromDate.getFullYear() === toDate.getFullYear()) {
      return `${fromDate.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })} - ${toDate.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })}`
    }

    // Different years, show full format
    return `${fromDate.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })} - ${toDate.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })}`
  }

  // Handle card clicks to toggle line visibility
  const handleCardClick = (lineType: keyof VisibleLines) => {
    setVisibleLines((prev) => {
      // If the clicked line is the only one visible, show all lines
      const visibleCount = Object.values(prev).filter(Boolean).length
      const isOnlyVisible = prev[lineType] && visibleCount === 1

      if (isOnlyVisible) {
        // Show all lines
        return {
          outbound: true,
          inbound: true,
          combined: true,
        }
      } else {
        // Show only the clicked line
        return {
          outbound: lineType === "outbound",
          inbound: lineType === "inbound",
          combined: lineType === "combined",
        }
      }
    })
  }

  return (
    <Card className="bg-card border-border shadow-xl">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-primary/10 rounded-md border border-primary/20">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-foreground">Inbound vs Outbound vs Total Trend</CardTitle>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-primary" />
            <Badge
              variant="outline"
              className="text-sm font-medium bg-primary/10 text-primary border-primary/50 px-3 py-1"
            >
              {formatDateRange()}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Interactive Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Outbound Card */}
          <div
            className={cn(
              "bg-card rounded-lg p-4 border border-border cursor-pointer transition-all duration-200 hover:bg-accent/5",
              visibleLines.outbound && !visibleLines.inbound && !visibleLines.combined
                ? "ring-2 ring-green-500 bg-green-500/5"
                : "hover:border-green-500/50",
            )}
            onClick={() => handleCardClick("outbound")}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-muted-foreground text-sm">Outbound</span>
            </div>
            <div className="text-2xl font-bold text-green-400">
              {Math.round(summaryStats.outbound.total).toLocaleString()} kg
            </div>
            <div className="flex justify-between items-center">
              <p className="text-xs text-muted-foreground">
                Weekly avg: {Math.round(summaryStats.outbound.avg).toLocaleString()} kg ({summaryStats.outbound.count}{" "}
                shipments)
              </p>
              <p className="text-xs text-muted-foreground">Total</p>
            </div>
          </div>

          {/* Inbound Card */}
          <div
            className={cn(
              "bg-card rounded-lg p-4 border border-border cursor-pointer transition-all duration-200 hover:bg-accent/5",
              visibleLines.inbound && !visibleLines.outbound && !visibleLines.combined
                ? "ring-2 ring-blue-500 bg-blue-500/5"
                : "hover:border-blue-500/50",
            )}
            onClick={() => handleCardClick("inbound")}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="text-muted-foreground text-sm">Inbound</span>
            </div>
            <div className="text-2xl font-bold text-blue-400">
              {Math.round(summaryStats.inbound.total).toLocaleString()} kg
            </div>
            <div className="flex justify-between items-center">
              <p className="text-xs text-muted-foreground">
                Weekly avg: {Math.round(summaryStats.inbound.avg).toLocaleString()} kg ({summaryStats.inbound.count}{" "}
                shipments)
              </p>
              <p className="text-xs text-muted-foreground">Total</p>
            </div>
          </div>

          {/* Total Card */}
          <div
            className={cn(
              "bg-card rounded-lg p-4 border border-border cursor-pointer transition-all duration-200 hover:bg-accent/5",
              visibleLines.combined && !visibleLines.outbound && !visibleLines.inbound
                ? "ring-2 ring-purple-500 bg-purple-500/5"
                : "hover:border-purple-500/50",
            )}
            onClick={() => handleCardClick("combined")}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
              <span className="text-muted-foreground text-sm">Total</span>
            </div>
            <div className="text-2xl font-bold text-purple-400">
              {Math.round(summaryStats.combined.total).toLocaleString()} kg
            </div>
            <div className="flex justify-between items-center">
              <p className="text-xs text-muted-foreground">
                Weekly avg: {Math.round(summaryStats.combined.avg).toLocaleString()} kg
              </p>
              <p className="text-xs text-muted-foreground">All Records</p>
            </div>
          </div>
        </div>

        {/* Line Chart */}
        <div className="h-80">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="weekLabel"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  interval={0}
                />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickFormatter={(value) => `${value} kg`} />
                <Tooltip
                  formatter={(value: number, name: string) => [`${value.toLocaleString()} kg`, name]}
                  labelFormatter={(label) => `Week: ${label}`}
                  contentStyle={{
                    backgroundColor: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    color: "hsl(var(--popover-foreground))",
                  }}
                />
                {/* Conditionally render lines based on visibility state */}
                {visibleLines.outbound && (
                  <Line
                    type="monotone"
                    dataKey="outbound"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                    name="Outbound"
                  />
                )}
                {visibleLines.inbound && (
                  <Line type="monotone" dataKey="inbound" stroke="#3b82f6" strokeWidth={2} dot={false} name="Inbound" />
                )}
                {visibleLines.combined && (
                  <Line
                    type="monotone"
                    dataKey="combined"
                    stroke="#a855f7"
                    strokeWidth={3}
                    dot={false}
                    name="Total"
                    strokeDasharray="5 5"
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full bg-muted/20 rounded-lg">
              <div className="text-center">
                <TrendingUp className="w-12 h-12 text-muted-foreground mx-auto mb-2" />
                <p className="text-muted-foreground">No trend data available</p>
                <p className="text-muted-foreground text-sm">
                  Total records: {data.length} | With KG: {data.filter((r) => r.KG && r.KG > 0).length} | With
                  Direction: {data.filter((r) => r["Out/In"]).length}
                </p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
