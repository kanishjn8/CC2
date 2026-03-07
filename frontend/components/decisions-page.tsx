"use client"

import { Fragment, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Brain,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  AlertTriangle,
  Eye,
  ChevronDown,
  ChevronUp,
  Navigation,
  Bell,
  Sparkles,
} from "lucide-react"
import { useDecisions, useAgentMetrics, useLlmStats } from "@/hooks/use-data"
import { cn, getRiskColor, getRiskLabel, formatPercent, formatTimeAgo } from "@/lib/utils"
import { api } from "@/lib/api"
import { ReasoningChain } from "@/components/reasoning-chain"
import type { RerouteResult } from "@/lib/types"
import { useRerouteContext } from "@/hooks/use-reroute-context"

interface DecisionsPageProps {
  onReroute?: (result: RerouteResult) => void
}

export default function DecisionsPage({ onReroute: onRerouteProp }: DecisionsPageProps) {
  const { setRerouteData } = useRerouteContext()
  const { data: decisions, loading, refetch } = useDecisions()
  const { data: metrics } = useAgentMetrics()
  const { data: llmStats } = useLlmStats()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [toast, setToast] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null)

  // Support both prop-based and context-based reroute notification
  const onReroute = (result: RerouteResult) => {
    setRerouteData(result)
    onRerouteProp?.(result)
  }

  const showToast = (type: "success" | "error" | "info", message: string) => {
    setToast({ type, message })
    setTimeout(() => setToast(null), 5000)
  }

  const handleApprove = async (decisionId: string, action: string) => {
    setActionLoading(decisionId)
    try {
      const res = await api.approveDecision(decisionId)

      // If this was a reroute action and we got route geometry back
      if (action === "reroute_shipment" && res.result) {
        const rerouteResult: RerouteResult = {
          status: "rerouted",
          shipment_id: res.result.old_route ? String(res.result.old_route) : "",
          old_route: res.result.old_route ? String(res.result.old_route) : null,
          new_route: res.result.new_route ? String(res.result.new_route) : null,
          new_route_origin: res.result.new_route_origin ? String(res.result.new_route_origin) : null,
          new_route_destination: res.result.new_route_destination ? String(res.result.new_route_destination) : null,
          eta_improvement_hours: Number(res.result.eta_improvement_hours ?? 0),
          old_route_geometry: res.result.old_route_geometry as RerouteResult["old_route_geometry"] ?? null,
          new_route_geometry: res.result.new_route_geometry as RerouteResult["new_route_geometry"] ?? null,
          message: `Rerouted: ETA improved by ${Number(res.result.eta_improvement_hours ?? 0).toFixed(1)}h`,
        }
        onReroute?.(rerouteResult)
        showToast("success", `✅ Reroute approved — ETA improved by ${rerouteResult.eta_improvement_hours.toFixed(1)}h. Check the map!`)
      } else {
        showToast("success", `✅ Action "${action}" approved and executed.`)
      }

      refetch()
    } catch {
      showToast("error", "Failed to approve action.")
    } finally {
      setActionLoading(null)
    }
  }

  const handleReject = async (decisionId: string) => {
    setActionLoading(decisionId)
    try {
      await api.rejectDecision(decisionId)
      showToast("info", "Action rejected.")
      refetch()
    } catch {
      showToast("error", "Failed to reject action.")
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  const pendingApproval = decisions.filter((d) => d.status === "pending_approval")

  function getOutcomeDisplay(outcome: string) {
    switch (outcome) {
      case "completed":
        return { icon: CheckCircle, color: "text-emerald-400", label: "Completed" }
      case "escalated":
        return { icon: AlertTriangle, color: "text-amber-400", label: "Escalated" }
      case "monitoring":
        return { icon: Eye, color: "text-primary", label: "Monitoring" }
      case "pending":
      default:
        return { icon: Clock, color: "text-muted-foreground", label: "Pending" }
    }
  }

  return (
    <div className="space-y-6">
      {/* Toast notification */}
      {toast && (
        <div
          className={cn(
            "fixed top-4 right-4 z-50 px-4 py-3 rounded-lg border shadow-lg text-sm font-medium animate-in slide-in-from-top-2 fade-in duration-300",
            toast.type === "success" && "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
            toast.type === "error" && "bg-red-500/15 text-red-400 border-red-500/30",
            toast.type === "info" && "bg-primary/15 text-primary border-primary/30",
          )}
        >
          {toast.message}
        </div>
      )}

      {/* Summary */}
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant="outline" className="bg-card px-3 py-1.5 text-sm">
          <Brain className="h-3 w-3 mr-1" />
          Total Decisions: {decisions.length}
        </Badge>
        {pendingApproval.length > 0 && (
          <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30 px-3 py-1.5 text-sm">
            <Shield className="h-3 w-3 mr-1" />
            Pending Approval: {pendingApproval.length}
          </Badge>
        )}
        <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 px-3 py-1.5 text-sm">
          Avg Confidence: {formatPercent(metrics.average_confidence)}
        </Badge>
        {llmStats.total_calls > 0 && (
          <Badge variant="outline" className="bg-purple-500/10 text-purple-400 border-purple-500/30 px-3 py-1.5 text-sm">
            <Sparkles className="h-3 w-3 mr-1" />
            LLM: {llmStats.total_calls} calls
            {llmStats.total_skipped > 0 && ` · ${llmStats.total_skipped} cooldown`}
            {llmStats.total_failures > 0 && ` · ${llmStats.total_failures} failed`}
          </Badge>
        )}
        {llmStats.api_key_set === false && (
          <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/30 px-3 py-1.5 text-sm">
            ⚠️ No LLM API Key
          </Badge>
        )}
      </div>

      {/* Decision Logs */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
            <Brain className="h-4 w-4" />
            AI Agent Decision Log — Explainable AI
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[40px]"></TableHead>
                <TableHead className="w-[100px]">Shipment</TableHead>
                <TableHead>Problem Detected</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Outcome</TableHead>
                <TableHead>Authorization</TableHead>
                <TableHead>Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {decisions.map((decision) => {
                const isExpanded = expandedId === decision.decision_id
                const outcomeInfo = getOutcomeDisplay(decision.outcome)
                const OutcomeIcon = outcomeInfo.icon
                const isPending = decision.status === "pending_approval"
                const isApproved = decision.status === "approved"
                const isRejected = decision.status === "rejected"

                return (
                  <Fragment key={decision.decision_id}>
                    <TableRow
                      className={cn(
                        "cursor-pointer transition-colors",
                        decision.risk_score >= 0.7 && "bg-red-500/5",
                        isExpanded && "bg-accent/50"
                      )}
                      onClick={() => setExpandedId(isExpanded ? null : decision.decision_id)}
                    >
                      <TableCell className="p-2">
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono font-semibold text-foreground text-xs">
                        {decision.shipment_id}
                      </TableCell>
                      <TableCell className="max-w-[250px]">
                        <span className="text-xs text-foreground line-clamp-1">
                          {decision.problem}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={cn("text-xs font-semibold", getRiskColor(decision.risk_score))}>
                          {(decision.risk_score * 100).toFixed(0)}% {getRiskLabel(decision.risk_score)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-muted-foreground">
                          {(decision.confidence * 100).toFixed(0)}%
                        </span>
                      </TableCell>
                      <TableCell className="max-w-[180px]">
                        <span className="text-xs text-primary line-clamp-1">
                          {decision.recommended_action}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={cn("inline-flex items-center gap-1 text-xs", outcomeInfo.color)}>
                          <OutcomeIcon className="h-3 w-3" />
                          {outcomeInfo.label}
                        </span>
                      </TableCell>
                      <TableCell>
                        {decision.requires_approval ? (
                          isPending ? (
                            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10"
                                disabled={actionLoading === decision.decision_id}
                                onClick={() => handleApprove(decision.decision_id, decision.recommended_action)}
                              >
                                <CheckCircle className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                                disabled={actionLoading === decision.decision_id}
                                onClick={() => handleReject(decision.decision_id)}
                              >
                                <XCircle className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          ) : (
                            <Badge
                              variant={isApproved ? "outline" : "destructive"}
                              className={cn(
                                "text-[10px]",
                                isApproved && "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                              )}
                            >
                              {isApproved ? "Approved" : isRejected ? "Rejected" : decision.status}
                            </Badge>
                          )
                        ) : (
                          <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/30">
                            Autonomous
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatTimeAgo(decision.created_at || "")}
                      </TableCell>
                    </TableRow>
                    {/* Expanded Reasoning Row */}
                    {isExpanded && (
                      <TableRow key={`${decision.decision_id}-detail`} className="bg-accent/30">
                        <TableCell colSpan={9} className="p-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <ReasoningChain decision={decision} />
                            <div className="space-y-3 text-xs">
                              <div>
                                <p className="font-semibold text-muted-foreground uppercase tracking-wide text-[10px] mb-1">
                                  Decision Metadata
                                </p>
                                <div className="space-y-1">
                                  <p><span className="text-muted-foreground">Risk Score:</span> <span className={getRiskColor(decision.risk_score)}>{(decision.risk_score * 100).toFixed(1)}%</span></p>
                                  <p><span className="text-muted-foreground">Confidence:</span> <span className="text-foreground">{(decision.confidence * 100).toFixed(1)}%</span></p>
                                  <p><span className="text-muted-foreground">Authorization:</span> <span className="text-foreground">{decision.requires_approval ? "Requires Approval" : "Autonomous"}</span></p>
                                  <p><span className="text-muted-foreground">SLA Impact:</span> <span className="text-primary">{decision.sla_impact != null ? `${decision.sla_impact} hrs` : "N/A"}</span></p>
                                </div>
                              </div>
                              {/* Show reroute result if approved and has geometry */}
                              {decision.status === "approved" && decision.recommended_action === "reroute_shipment" && decision.action_details && (() => {
                                try {
                                  const details = JSON.parse(decision.action_details)
                                  const result = details.approval_result
                                  if (result?.success) {
                                    return (
                                      <div className="mt-2 p-2 rounded-md bg-cyan-500/10 border border-cyan-500/20">
                                        <p className="font-semibold text-cyan-400 text-[10px] uppercase tracking-wide mb-1 flex items-center gap-1">
                                          <Navigation className="h-3 w-3" /> Reroute Result
                                        </p>
                                        <div className="space-y-0.5 text-[11px]">
                                          <p><span className="text-muted-foreground">Old Route:</span> <span className="text-red-400">{result.old_route}</span></p>
                                          <p><span className="text-muted-foreground">New Route:</span> <span className="text-cyan-400">{result.new_route}</span></p>
                                          <p><span className="text-muted-foreground">ETA Improved:</span> <span className="text-emerald-400">{Number(result.eta_improvement_hours).toFixed(1)}h</span></p>
                                          {result.new_route_geometry && (
                                            <Button
                                              size="sm"
                                              variant="outline"
                                              className="mt-1.5 h-6 text-[10px] text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/10"
                                              onClick={(e) => {
                                                e.stopPropagation()
                                                onReroute?.({
                                                  status: "rerouted",
                                                  shipment_id: decision.entity_id,
                                                  old_route: result.old_route,
                                                  new_route: result.new_route,
                                                  new_route_origin: result.new_route_origin ?? null,
                                                  new_route_destination: result.new_route_destination ?? null,
                                                  eta_improvement_hours: result.eta_improvement_hours,
                                                  old_route_geometry: result.old_route_geometry ?? null,
                                                  new_route_geometry: result.new_route_geometry ?? null,
                                                  message: `Rerouted: ETA improved by ${Number(result.eta_improvement_hours).toFixed(1)}h`,
                                                })
                                                showToast("info", "📍 Reroute shown on map — switch to Overview tab.")
                                              }}
                                            >
                                              <Navigation className="h-3 w-3 mr-1" />
                                              Show on Map
                                            </Button>
                                          )}
                                        </div>
                                      </div>
                                    )
                                  }
                                } catch { /* parse error */ }
                                return null
                              })()}
                              {/* Show alert info for send_alert actions */}
                              {decision.recommended_action === "send_alert" && decision.action_details && (() => {
                                try {
                                  const details = JSON.parse(decision.action_details)
                                  const msg = details.message || details.approval_result?.alert_message || ""
                                  if (msg) {
                                    return (
                                      <div className="mt-2 p-2 rounded-md bg-amber-500/10 border border-amber-500/20">
                                        <p className="font-semibold text-amber-400 text-[10px] uppercase tracking-wide mb-1 flex items-center gap-1">
                                          <Bell className="h-3 w-3" /> Alert Sent
                                        </p>
                                        <p className="text-[11px] text-foreground">{msg}</p>
                                      </div>
                                    )
                                  }
                                } catch { /* parse error */ }
                                return null
                              })()}
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
