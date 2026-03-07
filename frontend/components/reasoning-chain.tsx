"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import {
  Eye,
  Brain,
  Scale,
  Zap,
  ArrowRight,
} from "lucide-react"
import type { AgentDecision } from "@/lib/types"
import { getRiskColor } from "@/lib/utils"

interface ReasoningChainProps {
  decision: AgentDecision
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

function getStageContent(stage: string, decision: AgentDecision): string {
  switch (stage) {
    case "observe":
      return decision.problem
    case "reason":
      return decision.root_cause
    case "decide":
      return `Risk: ${(decision.risk_score * 100).toFixed(0)}% | Confidence: ${(decision.confidence * 100).toFixed(0)}% | SLA Impact: ${decision.sla_impact}`
    case "act":
      return decision.action_taken
    default:
      return ""
  }
}

export function ReasoningChain({ decision }: ReasoningChainProps) {
  return (
    <div className="flex flex-col gap-0">
      {STAGES.map((stage, i) => {
        const Icon = stage.icon
        const content = getStageContent(stage.key, decision)
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
                <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5">
                  {content}
                </p>
              </div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
