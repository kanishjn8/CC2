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
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
} from "recharts"
import { Truck, AlertTriangle, CheckCircle, TrendingDown } from "lucide-react"
import { useCarriers } from "@/hooks/use-data"
import { cn, formatPercent } from "@/lib/utils"

export default function CarriersPage() {
  const { data: carriers, loading } = useCarriers()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  const degraded = carriers.filter((c) => c.reliability_score < 0.6)

  const radarData = carriers.map((c) => ({
    name: c.name.split(" ")[0],
    reliability: Math.round(c.reliability_score * 100),
    pickup: Math.round(c.pickup_success_rate * 100),
    onTime: Math.round((1 - c.delay_probability) * 100),
  }))

  const barData = carriers.map((c) => ({
    name: c.name.split(" ")[0],
    delay: Math.round(c.delay_probability * 100),
    reliability: Math.round(c.reliability_score * 100),
  }))

  function getReliabilityColor(score: number): string {
    if (score >= 0.8) return "text-emerald-400"
    if (score >= 0.6) return "text-amber-400"
    return "text-red-400"
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant="outline" className="bg-card px-3 py-1.5 text-sm">
          <Truck className="h-3 w-3 mr-1" />
          Total: {carriers.length}
        </Badge>
        {degraded.length > 0 && (
          <Badge variant="destructive" className="px-3 py-1.5 text-sm">
            <TrendingDown className="h-3 w-3 mr-1" />
            Degraded: {degraded.length}
          </Badge>
        )}
      </div>

      {/* Carrier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {carriers.map((carrier) => {
          const isDegraded = carrier.reliability_score < 0.6

          return (
            <Card
              key={carrier.carrier_id}
              className={cn(
                "border transition-all",
                isDegraded ? "border-red-500/30 bg-red-500/5" : "border-border"
              )}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold text-foreground">
                    {carrier.name}
                  </CardTitle>
                  {isDegraded ? (
                    <Badge variant="destructive" className="text-[10px]">
                      <AlertTriangle className="h-2.5 w-2.5 mr-1" />
                      DEGRADED
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                      <CheckCircle className="h-2.5 w-2.5 mr-1" />
                      HEALTHY
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{carrier.carrier_id}</p>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Reliability */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Reliability Score</span>
                    <span className={cn("font-semibold", getReliabilityColor(carrier.reliability_score))}>
                      {formatPercent(carrier.reliability_score)}
                    </span>
                  </div>
                  <Progress value={carrier.reliability_score * 100} />
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-accent p-3">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Delay Prob.</p>
                    <p className={cn(
                      "text-lg font-bold",
                      carrier.delay_probability >= 0.3 ? "text-red-400" : "text-foreground"
                    )}>
                      {formatPercent(carrier.delay_probability)}
                    </p>
                  </div>
                  <div className="rounded-lg bg-accent p-3">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Pickup Rate</p>
                    <p className={cn(
                      "text-lg font-bold",
                      carrier.pickup_success_rate >= 0.9 ? "text-emerald-400" : "text-foreground"
                    )}>
                      {formatPercent(carrier.pickup_success_rate)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <Card className="bg-black/60 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Carrier Performance Comparison
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={320} style={{ backgroundColor: "transparent" }}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="hsl(240, 3.7%, 15.9%)" />
                <PolarAngleAxis dataKey="name" tick={{ fill: "#71717a", fontSize: 11 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#71717a", fontSize: 9 }} />
                <Radar name="Reliability" dataKey="reliability" stroke="hsl(199, 89%, 48%)" fill="hsl(199, 89%, 48%)" fillOpacity={0.2} />
                <Radar name="Pickup Rate" dataKey="pickup" stroke="#10b981" fill="#10b981" fillOpacity={0.1} />
                <Radar name="On-Time %" dataKey="onTime" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.1} />
                <Legend
                  formatter={(value) => (
                    <span className="text-xs text-muted-foreground">{value}</span>
                  )}
                />
                <Tooltip
                  cursor={{ fill: "hsl(240, 4%, 16%, 0.5)" }}
                  wrapperStyle={{ outline: "none" }}
                  contentStyle={{
                    backgroundColor: "hsl(0, 0%, 3.9%)",
                    border: "1px solid hsl(240, 3.7%, 15.9%)",
                    borderRadius: "8px",
                    color: "#fafafa",
                  }}
                  formatter={(value: number) => [`${value}%`]}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Bar Chart - Delay vs Reliability */}
        <Card className="bg-black/60 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Delay Probability vs Reliability
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={320} style={{ backgroundColor: "transparent" }}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(240, 3.7%, 15.9%)" />
                <XAxis dataKey="name" tick={{ fill: "#71717a", fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: "#71717a", fontSize: 11 }} />
                <Tooltip
                  cursor={{ fill: "hsl(240, 4%, 16%, 0.5)" }}
                  wrapperStyle={{ outline: "none" }}
                  contentStyle={{
                    backgroundColor: "hsl(0, 0%, 3.9%)",
                    border: "1px solid hsl(240, 3.7%, 15.9%)",
                    borderRadius: "8px",
                    color: "#fafafa",
                  }}
                  formatter={(value: number) => [`${value}%`]}
                />
                <Legend
                  formatter={(value) => (
                    <span className="text-xs text-muted-foreground">{value}</span>
                  )}
                />
                <Bar dataKey="reliability" name="Reliability" fill="hsl(199, 89%, 48%)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="delay" name="Delay %" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
