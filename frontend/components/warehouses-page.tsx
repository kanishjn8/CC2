"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { Warehouse, AlertTriangle, ArrowUp } from "lucide-react"
import { useWarehouses } from "@/hooks/use-data"
import { cn, getCongestionColor, formatPercent } from "@/lib/utils"

export default function WarehousesPage() {
  const { data: warehouses, loading } = useWarehouses()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  const congested = warehouses.filter((w) => w.congestion_score >= 0.8)
  const chartData = warehouses.map((w) => ({
    name: w.location,
    utilization: Math.round((w.current_load / w.capacity) * 100),
    queue: w.queue_length,
  }))

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant="outline" className="bg-card px-3 py-1.5 text-sm">
          <Warehouse className="h-3 w-3 mr-1" />
          Total: {warehouses.length}
        </Badge>
        {congested.length > 0 && (
          <Badge variant="destructive" className="px-3 py-1.5 text-sm">
            <AlertTriangle className="h-3 w-3 mr-1" />
            Congested: {congested.length}
          </Badge>
        )}
      </div>

      {/* Warehouse Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {warehouses.map((wh) => {
          const utilPct = Math.round((wh.current_load / wh.capacity) * 100)
          const isCongested = wh.congestion_score >= 0.8

          return (
            <Card
              key={wh.warehouse_id}
              className={cn(
                "border transition-all",
                isCongested ? "border-red-500/30 bg-red-500/5" : "border-border"
              )}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold text-foreground">
                    {wh.name}
                  </CardTitle>
                  {isCongested && (
                    <Badge variant="destructive" className="text-[10px]">
                      CONGESTED
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{wh.warehouse_id} · {wh.location}</p>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Utilization */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Capacity Utilization</span>
                    <span className={cn("font-semibold", getCongestionColor(wh.congestion_score))}>
                      {utilPct}%
                    </span>
                  </div>
                  <Progress value={utilPct} />
                  <p className="text-[10px] text-muted-foreground">
                    {wh.current_load} / {wh.capacity} units
                  </p>
                </div>

                {/* Metrics Row */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-accent p-3">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Queue Length</p>
                    <p className="text-lg font-bold text-foreground">{wh.queue_length}</p>
                  </div>
                  <div className="rounded-lg bg-accent p-3">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Congestion</p>
                    <p className={cn("text-lg font-bold", getCongestionColor(wh.congestion_score))}>
                      {formatPercent(wh.congestion_score)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Utilization Bar Chart */}
      <Card className="bg-black/60 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-muted-foreground">
            Warehouse Utilization Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={320} style={{ backgroundColor: "transparent" }}>
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(240, 3.7%, 15.9%)" />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: "#71717a", fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={100} tick={{ fill: "#71717a", fontSize: 11 }} />
              <Tooltip
                cursor={{ fill: "hsl(240, 4%, 16%, 0.5)" }}
                wrapperStyle={{ outline: "none" }}
                contentStyle={{
                  backgroundColor: "hsl(0, 0%, 3.9%)",
                  border: "1px solid hsl(240, 3.7%, 15.9%)",
                  borderRadius: "8px",
                  color: "#fafafa",
                }}
                formatter={(value: number) => [`${value}%`, "Utilization"]}
              />
              <Bar
                dataKey="utilization"
                radius={[0, 4, 4, 0]}
                fill="hsl(199, 89%, 48%)"
              />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
