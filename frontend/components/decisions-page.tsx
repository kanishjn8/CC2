"use client"

import { useState } from "react"
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
} from "lucide-react"
import { useDecisions, useAgentMetrics } from "@/hooks/use-data"
import { cn, getRiskColor, getRiskLabel, formatPercent, formatTimeAgo } from "@/lib/utils"
import { api } from "@/lib/api"
import { ReasoningChain } from "@/components/reasoning-chain"

export default function DecisionsPage() {
  const { data: decisions, loading, refetch } = useDecisions()
  const { data: metrics } = useAgentMetrics()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const handleApprove = async (logId: string) => {
    setActionLoading(logId)
    try {
      await api.approveAction(logId)
      refetch()
    } catch {
      // Silent fallback — mock mode
    } finally {
      setActionLoading(null)
    }
  }

  const handleReject = async (logId: string) => {
    setActionLoading(logId)
    try {
      await api.rejectAction(logId)
      refetch()
    } catch {
      // Silent fallback — mock mode
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

  const pendingApproval = decisions.filter((d) => d.requires_approval && d.approved === null)

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
          Accuracy: {formatPercent(metrics.prediction_accuracy)}
        </Badge>
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
                const isExpanded = expandedId === decision.log_id
                const outcomeInfo = getOutcomeDisplay(decision.outcome)
                const OutcomeIcon = outcomeInfo.icon

                return (
                  <>
                    <TableRow
                      key={decision.log_id}
                      className={cn(
                        "cursor-pointer transition-colors",
                        decision.risk_score >= 0.7 && "bg-red-500/5",
                        isExpanded && "bg-accent/50"
                      )}
                      onClick={() => setExpandedId(isExpanded ? null : decision.log_id)}
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
                          {decision.action_taken}
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
                          decision.approved === null ? (
                            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10"
                                disabled={actionLoading === decision.log_id}
                                onClick={() => handleApprove(decision.log_id)}
                              >
                                <CheckCircle className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                                disabled={actionLoading === decision.log_id}
                                onClick={() => handleReject(decision.log_id)}
                              >
                                <XCircle className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          ) : (
                            <Badge
                              variant={decision.approved ? "outline" : "destructive"}
                              className={cn(
                                "text-[10px]",
                                decision.approved && "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                              )}
                            >
                              {decision.approved ? "Approved" : "Rejected"}
                            </Badge>
                          )
                        ) : (
                          <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/30">
                            Autonomous
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatTimeAgo(decision.timestamp)}
                      </TableCell>
                    </TableRow>
                    {/* Expanded Reasoning Row */}
                    {isExpanded && (
                      <TableRow key={`${decision.log_id}-detail`} className="bg-accent/30">
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
                                  <p><span className="text-muted-foreground">SLA Impact:</span> <span className="text-primary">{decision.sla_impact}</span></p>
                                </div>
                              </div>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
