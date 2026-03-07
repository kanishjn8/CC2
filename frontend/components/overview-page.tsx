"use client"

import { useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Package,
  AlertTriangle,
  ShieldAlert,
  Activity,
  Truck,
  Warehouse,
  Radio,
  X,
  Navigation,
} from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts"
import { useShipments, useWarehouses, useCarriers, useAgentMetrics, useSimulationStatus } from "@/hooks/use-data"
import { cn, getHealthColor, formatPercent } from "@/lib/utils"
import dynamic from "next/dynamic"
import { motion } from "framer-motion"
import { AnimatedCounter } from "@/components/animated-counter"
import { LiveActivityFeed } from "@/components/live-activity-feed"
import { useRerouteContext } from "@/hooks/use-reroute-context"

const ShipmentMap = dynamic(() => import("@/components/shipment-map"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[450px] bg-accent/30 rounded-lg">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  ),
})

export default function OverviewPage() {
  const { data: shipments, loading: shipmentsLoading } = useShipments()
  const { data: warehouses } = useWarehouses()
  const { data: carriers } = useCarriers()
  const { data: metrics } = useAgentMetrics()
  const { data: simStatus } = useSimulationStatus()
  const { rerouteData, clearReroute } = useRerouteContext()

  // Compute overview stats from real data
  const overview = useMemo(() => {
    const totalShipments = shipments.length
    const delayed = shipments.filter((s) => s.status === "delayed" || s.status === "failed")
    const shipmentsAtRisk = delayed.length

    // Predicted SLA breaches: shipments where ETA > SLA deadline
    const slaBreaches = shipments.filter((s) => {
      if (s.status === "delivered") return false
      return new Date(s.eta) > new Date(s.sla_deadline)
    }).length

    // Network health: based on avg warehouse utilisation, carrier reliability, and on-time rate
    const avgCongestion = warehouses.length
      ? warehouses.reduce((sum, w) => sum + w.congestion_score, 0) / warehouses.length
      : 0
    const avgReliability = carriers.length
      ? carriers.reduce((sum, c) => sum + c.reliability_score, 0) / carriers.length
      : 1
    const onTimeRate = totalShipments
      ? 1 - shipmentsAtRisk / totalShipments
      : 1
    const healthScore = Math.round(
      ((1 - avgCongestion) * 0.3 + avgReliability * 0.4 + onTimeRate * 0.3) * 100
    )

    // Status distribution for the pie chart
    const statusCounts: Record<string, number> = {}
    shipments.forEach((s) => {
      statusCounts[s.status] = (statusCounts[s.status] || 0) + 1
    })
    const statusDistribution = [
      { level: "Delayed/Failed", count: (statusCounts["delayed"] || 0) + (statusCounts["failed"] || 0), color: "#ef4444" },
      { level: "In Transit", count: statusCounts["in_transit"] || 0, color: "#f59e0b" },
      { level: "Delivered", count: statusCounts["delivered"] || 0, color: "#10b981" },
      { level: "Dispatched", count: statusCounts["dispatched"] || 0, color: "#3b82f6" },
      { level: "Created", count: statusCounts["created"] || 0, color: "#8b5cf6" },
    ].filter((b) => b.count > 0)

    return {
      totalShipments,
      shipmentsAtRisk,
      slaBreaches,
      healthScore,
      activeCarriers: carriers.length,
      activeWarehouses: warehouses.length,
      statusDistribution,
    }
  }, [shipments, warehouses, carriers])

  // Warehouse utilization chart data
  const warehouseChartData = useMemo(() =>
    warehouses.map((w) => ({
      name: w.location,
      utilization: Math.round((w.current_load / w.capacity) * 100),
    })),
    [warehouses]
  )

  if (shipmentsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  const kpiCards = [
    {
      title: "Total Shipments",
      value: overview.totalShipments,
      icon: Package,
      color: "text-primary",
      bgColor: "bg-primary/10 border-primary/20",
    },
    {
      title: "Delayed / Failed",
      value: overview.shipmentsAtRisk,
      icon: AlertTriangle,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10 border-amber-500/20",
    },
    {
      title: "SLA Breaches",
      value: overview.slaBreaches,
      icon: ShieldAlert,
      color: "text-red-400",
      bgColor: "bg-red-500/10 border-red-500/20",
    },
    {
      title: "Network Health",
      value: `${overview.healthScore}%`,
      icon: Activity,
      color: getHealthColor(overview.healthScore),
      bgColor: overview.healthScore >= 80
        ? "bg-emerald-500/10 border-emerald-500/20"
        : overview.healthScore >= 60
        ? "bg-amber-500/10 border-amber-500/20"
        : "bg-red-500/10 border-red-500/20",
    },
    {
      title: "Active Carriers",
      value: overview.activeCarriers,
      icon: Truck,
      color: "text-purple-400",
      bgColor: "bg-purple-500/10 border-purple-500/20",
    },
    {
      title: "Active Warehouses",
      value: overview.activeWarehouses,
      icon: Warehouse,
      color: "text-cyan-400",
      bgColor: "bg-cyan-500/10 border-cyan-500/20",
    },
  ]

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {kpiCards.map((kpi, i) => {
          const Icon = kpi.icon
          return (
            <motion.div
              key={kpi.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06, duration: 0.4 }}
            >
              <Card className={cn("border", kpi.bgColor)}>
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className={cn("p-2 rounded-lg bg-background/50")}>
                      <Icon className={cn("h-5 w-5", kpi.color)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-muted-foreground">{kpi.title}</p>
                      <AnimatedCounter
                        value={kpi.value}
                        className={cn("text-2xl font-bold", kpi.color)}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* Live Shipment Map */}
      <Card className="bg-black/60 backdrop-blur-sm">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Live Shipment Network
            </CardTitle>
            <div className="flex items-center gap-2">
              {rerouteData && (
                <Badge className="bg-cyan-500/15 text-cyan-400 border-cyan-500/30 gap-1">
                  <Navigation className="h-3 w-3" />
                  Reroute Active
                  <button onClick={clearReroute} className="ml-1 hover:text-cyan-200">
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )}
              <Badge variant="outline" className="text-[10px] gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {shipments.filter((s) => s.status === "in_transit").length} active routes
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0 pb-4">
          {/* Reroute info banner */}
          {rerouteData && (
            <div className="mx-4 mb-3 p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-between">
              <div className="flex items-center gap-3 text-xs">
                <Navigation className="h-4 w-4 text-cyan-400 shrink-0" />
                <div>
                  <span className="text-cyan-400 font-semibold">Reroute Visualization Active</span>
                  <span className="text-muted-foreground ml-2">
                    {rerouteData.old_route} → {rerouteData.new_route}
                  </span>
                  <span className="text-emerald-400 ml-2">
                    ETA improved by {rerouteData.eta_improvement_hours.toFixed(1)}h
                  </span>
                </div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-muted-foreground hover:text-foreground"
                onClick={clearReroute}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
          <ShipmentMap shipments={shipments} rerouteData={rerouteData} />
        </CardContent>
      </Card>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Warehouse Utilization Chart */}
        <Card className="lg:col-span-2 bg-black/60 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Warehouse Utilization
            </CardTitle>
          </CardHeader>
          <CardContent>
            {warehouseChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={warehouseChartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(240, 3.7%, 15.9%)" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: "#71717a", fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={110} tick={{ fill: "#71717a", fontSize: 11 }} />
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
                  <Bar dataKey="utilization" radius={[0, 4, 4, 0]} fill="hsl(199, 89%, 48%)" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-12">No warehouse data available</p>
            )}
          </CardContent>
        </Card>

        {/* Status Distribution Pie */}
        <Card className="bg-black/60 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Shipment Status Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            {overview.statusDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={overview.statusDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={4}
                    dataKey="count"
                    nameKey="level"
                    strokeWidth={0}
                  >
                    {overview.statusDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Legend
                    formatter={(value) => (
                      <span style={{ color: "#a1a1aa", fontSize: "12px" }}>{value}</span>
                    )}
                    wrapperStyle={{ paddingTop: "16px" }}
                  />
                  <Tooltip
                    cursor={{ fill: "hsl(240, 4%, 16%, 0.5)" }}
                    wrapperStyle={{ outline: "none", zIndex: 9999 }}
                    contentStyle={{
                      backgroundColor: "hsl(0, 0%, 3.9%)",
                      border: "1px solid hsl(240, 3.7%, 15.9%)",
                      borderRadius: "8px",
                      color: "#fafafa",
                    }}
                    itemStyle={{ color: "#fafafa", fontSize: "12px" }}
                    labelStyle={{ color: "#a1a1aa", fontSize: "11px" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-12">No shipment data yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Activity Feed + Agent Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Activity Feed */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
              <Radio className="h-4 w-4 text-primary animate-pulse" />
              Live Agent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <LiveActivityFeed />
          </CardContent>
        </Card>

        {/* Agent Performance Metrics */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              AI Agent Performance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Intervention Success</p>
                <p className="text-3xl font-bold text-emerald-400">
                  {formatPercent(metrics.intervention_success_rate)}
                </p>
                <div className="h-2 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all"
                    style={{ width: `${metrics.intervention_success_rate * 100}%` }}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Avg Confidence</p>
                <p className="text-3xl font-bold text-primary">
                  {formatPercent(metrics.average_confidence)}
                </p>
                <div className="h-2 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${metrics.average_confidence * 100}%` }}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">False Positive Rate</p>
                <p className="text-3xl font-bold text-amber-400">
                  {formatPercent(metrics.false_positive_rate)}
                </p>
                <div className="h-2 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full bg-amber-500 transition-all"
                    style={{ width: `${metrics.false_positive_rate * 100}%` }}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Total Decisions</p>
                <p className="text-3xl font-bold text-foreground">{metrics.total_decisions}</p>
                <Badge variant="outline" className="text-xs">
                  Sim time: {simStatus.sim_time.toFixed(1)}h
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
