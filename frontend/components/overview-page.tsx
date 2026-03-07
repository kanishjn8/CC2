"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Package,
  AlertTriangle,
  ShieldAlert,
  Activity,
  Truck,
  Warehouse,
  Radio,
} from "lucide-react"
import {
  AreaChart,
  Area,
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
import { useOverview, useAgentMetrics, useShipments } from "@/hooks/use-data"
import { cn, getHealthColor, formatPercent } from "@/lib/utils"
import dynamic from "next/dynamic"
import { motion } from "framer-motion"
import { AnimatedCounter } from "@/components/animated-counter"
import { Sparkline } from "@/components/sparkline"
import { LiveActivityFeed } from "@/components/live-activity-feed"

const ShipmentMap = dynamic(() => import("@/components/shipment-map"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[450px] bg-accent/30 rounded-lg">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  ),
})

export default function OverviewPage() {
  const { data: overview, loading } = useOverview()
  const { data: metrics } = useAgentMetrics()
  const { data: shipments } = useShipments()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  const kpiCards = [
    {
      title: "Total Shipments",
      value: overview.total_shipments,
      icon: Package,
      color: "text-primary",
      bgColor: "bg-primary/10 border-primary/20",
      sparkData: overview.shipment_trend.map((t) => t.count),
      sparkColor: "hsl(199, 89%, 48%)",
    },
    {
      title: "Shipments at Risk",
      value: overview.shipments_at_risk,
      icon: AlertTriangle,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10 border-amber-500/20",
      sparkData: overview.shipment_trend.map((t) => t.at_risk),
      sparkColor: "#f59e0b",
    },
    {
      title: "Predicted SLA Breaches",
      value: overview.predicted_sla_breaches,
      icon: ShieldAlert,
      color: "text-red-400",
      bgColor: "bg-red-500/10 border-red-500/20",
      sparkData: [1, 1, 2, 2, 3, 3, 2, 3, 3, 3],
      sparkColor: "#ef4444",
    },
    {
      title: "Network Health",
      value: `${overview.network_health_score}%`,
      icon: Activity,
      color: getHealthColor(overview.network_health_score),
      bgColor: overview.network_health_score >= 80
        ? "bg-emerald-500/10 border-emerald-500/20"
        : overview.network_health_score >= 60
        ? "bg-amber-500/10 border-amber-500/20"
        : "bg-red-500/10 border-red-500/20",
      sparkData: [65, 68, 70, 72, 71, 73, 72, 72, 71, 72],
      sparkColor: "#10b981",
    },
    {
      title: "Active Carriers",
      value: overview.active_carriers,
      icon: Truck,
      color: "text-purple-400",
      bgColor: "bg-purple-500/10 border-purple-500/20",
      sparkData: [4, 5, 5, 5, 5, 5, 5, 5, 5, 5],
      sparkColor: "#a855f7",
    },
    {
      title: "Active Warehouses",
      value: overview.active_warehouses,
      icon: Warehouse,
      color: "text-cyan-400",
      bgColor: "bg-cyan-500/10 border-cyan-500/20",
      sparkData: [6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
      sparkColor: "#22d3ee",
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
                      <div className="flex items-center gap-2">
                        <AnimatedCounter
                          value={kpi.value}
                          className={cn("text-2xl font-bold", kpi.color)}
                        />
                        <Sparkline
                          data={kpi.sparkData}
                          color={kpi.sparkColor}
                          width={48}
                          height={20}
                        />
                      </div>
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
            <Badge variant="outline" className="text-[10px] gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              {shipments.filter((s) => s.status === "in_transit").length} active routes
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0 pb-4">
          <ShipmentMap shipments={shipments} />
        </CardContent>
      </Card>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Shipment Trend Chart */}
        <Card className="lg:col-span-2 bg-black/60 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Shipment Volume & Risk Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={overview.shipment_trend}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(199, 89%, 48%)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(199, 89%, 48%)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(240, 3.7%, 15.9%)" />
                <XAxis dataKey="time" tick={{ fill: "#71717a", fontSize: 11 }} />
                <YAxis tick={{ fill: "#71717a", fontSize: 11 }} />
                <Tooltip
                  cursor={{ fill: "hsl(240, 4%, 16%, 0.5)" }}
                  wrapperStyle={{ outline: "none" }}
                  contentStyle={{
                    backgroundColor: "hsl(0, 0%, 3.9%)",
                    border: "1px solid hsl(240, 3.7%, 15.9%)",
                    borderRadius: "8px",
                    color: "#fafafa",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="hsl(199, 89%, 48%)"
                  fillOpacity={1}
                  fill="url(#colorCount)"
                  strokeWidth={2}
                  name="Total"
                />
                <Area
                  type="monotone"
                  dataKey="at_risk"
                  stroke="#ef4444"
                  fillOpacity={1}
                  fill="url(#colorRisk)"
                  strokeWidth={2}
                  name="At Risk"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Risk Distribution Pie */}
        <Card className="bg-black/60 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Risk Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={overview.risk_distribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={4}
                  dataKey="count"
                  nameKey="level"
                  strokeWidth={0}
                >
                  {overview.risk_distribution.map((entry, index) => (
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
                    padding: "8px 12px",
                  }}
                  itemStyle={{ color: "#fafafa", fontSize: "12px" }}
                  labelStyle={{ color: "#a1a1aa", fontSize: "11px", marginBottom: "4px" }}
                />
              </PieChart>
            </ResponsiveContainer>
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
              <p className="text-xs text-muted-foreground">Intervention Success Rate</p>
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
              <p className="text-xs text-muted-foreground">Prediction Accuracy</p>
              <p className="text-3xl font-bold text-primary">
                {formatPercent(metrics.prediction_accuracy)}
              </p>
              <div className="h-2 rounded-full bg-secondary overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${metrics.prediction_accuracy * 100}%` }}
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
              <p className="text-xs text-muted-foreground">Total Decisions Made</p>
              <p className="text-3xl font-bold text-foreground">{metrics.total_decisions}</p>
              <Badge variant="outline" className="text-xs">
                Last 24 hours
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
      </div>
    </div>
  )
}
