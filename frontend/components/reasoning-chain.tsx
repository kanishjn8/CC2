"use client"

import { useMemo } from "react"
import type { ReactNode } from "react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import {
  Eye,
  Brain,
  Scale,
  Zap,
  Sparkles,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { AgentDecision } from "@/lib/types"

interface ReasoningChainProps {
  decision: AgentDecision
}

/** Safely parse the action_details JSON blob from the decision. */
function parseActionDetails(decision: AgentDecision): {
  actionScores: Array<{ action: string; total_score: number; requires_approval: boolean; scores?: Record<string, number> }>
  llmTiebreaker: boolean
  llmReasoning: string
  llmGenerated: boolean
} {
  const defaults = { actionScores: [], llmTiebreaker: false, llmReasoning: "", llmGenerated: false }
  if (!decision.action_details) return defaults

  try {
    const details = typeof decision.action_details === "string"
      ? JSON.parse(decision.action_details)
      : decision.action_details

    const scores = details.action_scores ?? []
    const bestAction = scores[0] ?? {}
    return {
      actionScores: scores,
      llmTiebreaker: bestAction.llm_tiebreaker === true,
      llmReasoning: bestAction.llm_reasoning ?? details.approval_result?.llm_reasoning ?? "",
      llmGenerated: false, // will be overridden below
    }
  } catch {
    return defaults
  }
}

/** Parse the evidence JSON blob. */
function parseEvidence(decision: AgentDecision): Record<string, string | number> | null {
  if (!decision.evidence) return null
  try {
    return typeof decision.evidence === "string"
      ? JSON.parse(decision.evidence)
      : decision.evidence as Record<string, string | number>
  } catch {
    return null
  }
}

const STAGES = [
  {
    key: "observe",
    label: "Observe",
    icon: Eye,
    color: "text-primary",
    borderColor: "border-primary/30",
    bgColor: "bg-primary/10",
  },
  {
    key: "reason",
    label: "Reason",
    icon: Brain,
    color: "text-purple-400",
    borderColor: "border-purple-500/30",
    bgColor: "bg-purple-500/10",
  },
  {
    key: "decide",
    label: "Decide",
    icon: Scale,
    color: "text-amber-400",
    borderColor: "border-amber-500/30",
    bgColor: "bg-amber-500/10",
  },
  {
    key: "act",
    label: "Act",
    icon: Zap,
    color: "text-emerald-400",
    borderColor: "border-emerald-500/30",
    bgColor: "bg-emerald-500/10",
  },
]

export function ReasoningChain({ decision }: ReasoningChainProps) {
  const details = useMemo(() => parseActionDetails(decision), [decision])
  const evidence = useMemo(() => parseEvidence(decision), [decision])

  /** Is the root_cause from the LLM? Check evidence or action_details for the flag. */
  const llmGenerated = useMemo(() => {
    // The flag is set by reasoning.py but stored alongside evidence in the decision log
    try {
      if (decision.action_details) {
        const d = typeof decision.action_details === "string"
          ? JSON.parse(decision.action_details) : decision.action_details
        if (d.llm_generated === true) return true
      }
    } catch { /* ignore */ }
    // Heuristic: LLM-generated text tends to be longer and more natural
    return decision.root_cause?.length > 120
  }, [decision])

  function getStageContent(stage: string): ReactNode {
    switch (stage) {
      case "observe":
        return (
          <div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              {decision.problem}
            </p>
            {evidence && Object.keys(evidence).length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {Object.entries(evidence).map(([k, v]) => (
                  <span
                    key={k}
                    className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground"
                  >
                    <span className="font-medium">{k.replace(/_/g, " ")}:</span>
                    <span>{String(v)}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        )
      case "reason":
        return (
          <div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              {decision.root_cause}
            </p>
            {llmGenerated && (
              <Badge variant="outline" className="mt-1 text-[9px] gap-1 border-purple-500/40 text-purple-400">
                <Sparkles className="h-2.5 w-2.5" /> LLM Generated
              </Badge>
            )}
          </div>
        )
      case "decide":
        return (
          <div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Risk: {(decision.risk_score * 100).toFixed(0)}% | Confidence: {(decision.confidence * 100).toFixed(0)}%
              {decision.sla_impact != null && ` | SLA Impact: ${decision.sla_impact} hrs`}
            </p>
            {/* Action scores breakdown */}
            {details.actionScores.length > 0 && (
              <div className="mt-1.5 space-y-0.5">
                {details.actionScores.slice(0, 3).map((s, i) => (
                  <div key={s.action} className="flex items-center gap-2 text-[10px]">
                    <span className={cn(
                      "font-mono",
                      i === 0 ? "text-amber-400 font-semibold" : "text-muted-foreground"
                    )}>
                      {(s.total_score * 100).toFixed(0)}%
                    </span>
                    <div
                      className={cn(
                        "h-1 rounded-full",
                        i === 0 ? "bg-amber-400" : "bg-muted-foreground/30"
                      )}
                      style={{ width: `${s.total_score * 80}px` }}
                    />
                    <span className="text-muted-foreground">
                      {s.action.replace(/_/g, " ")}
                      {s.requires_approval && " 🔒"}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {/* LLM tiebreaker reasoning */}
            {details.llmTiebreaker && details.llmReasoning && (
              <div className="mt-1.5 p-1.5 rounded bg-purple-500/5 border border-purple-500/20">
                <div className="flex items-center gap-1 text-[9px] text-purple-400 font-semibold mb-0.5">
                  <Sparkles className="h-2.5 w-2.5" /> LLM Tiebreaker
                </div>
                <p className="text-[10px] text-muted-foreground leading-relaxed italic">
                  &ldquo;{details.llmReasoning}&rdquo;
                </p>
              </div>
            )}
          </div>
        )
      case "act":
        return (
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            <span className="font-semibold text-foreground">
              {decision.recommended_action.replace(/_/g, " ")}
            </span>
            {decision.requires_approval && (
              <Badge variant="outline" className="ml-1.5 text-[9px] border-amber-500/40 text-amber-400">
                Approval Required
              </Badge>
            )}
          </p>
        )
      default:
        return null
    }
  }

  return (
    <div className="flex flex-col gap-0">
      {STAGES.map((stage, i) => {
        const Icon = stage.icon
        const content = getStageContent(stage.key)
        return (
          <motion.div
            key={stage.key}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.12, duration: 0.3 }}
          >
            <div className="flex items-start gap-3">
              {/* Step indicator column */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "h-8 w-8 rounded-full flex items-center justify-center border",
                    stage.bgColor,
                    stage.borderColor
                  )}
                >
                  <Icon className={cn("h-4 w-4", stage.color)} />
                </div>
                {i < STAGES.length - 1 && (
                  <div className="w-px h-6 bg-muted-foreground/20 my-1" />
                )}
              </div>
              {/* Content */}
              <div className="flex-1 pb-2">
                <p className={cn("text-xs font-semibold", stage.color)}>
                  {stage.label}
                </p>
                <div className="mt-0.5">
                  {content}
                </div>
              </div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
