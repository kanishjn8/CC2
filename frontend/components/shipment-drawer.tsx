"use client"

import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  MapPin,
  Clock,
  AlertTriangle,
  Truck,
  CheckCircle,
  ArrowRight,
} from "lucide-react"
import type { Shipment } from "@/lib/types"
import { cn, getRiskColor, getRiskLabel, formatTimestamp } from "@/lib/utils"

interface ShipmentDrawerProps {
  shipment: Shipment | null
  open: boolean
  onClose: () => void
}

const STATUS_STEPS = ["created", "dispatched", "in_transit", "delivered"] as const
const STATUS_LABELS: Record<string, string> = {
  created: "Created",
  dispatched: "Dispatched",
  in_transit: "In Transit",
  delivered: "Delivered",
  delayed: "Delayed",
  at_risk: "At Risk",
}

export function ShipmentDrawer({ shipment, open, onClose }: ShipmentDrawerProps) {
  if (!shipment) return null

  const currentStepIdx = STATUS_STEPS.indexOf(
    shipment.status as (typeof STATUS_STEPS)[number]
  )
  const isDelayed = shipment.status === "delayed" || shipment.status === "at_risk"

  const slaDeadline = new Date(shipment.sla_deadline)
  const eta = new Date(shipment.eta)
  const willBreachSla = eta > slaDeadline

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent
        side="right"
        className="w-[420px] sm:max-w-[420px] bg-black/90 backdrop-blur-xl border-white/[0.08] overflow-y-auto"
      >
        <SheetHeader className="pb-4 border-b border-white/[0.06]">
          <SheetTitle className="text-lg font-bold text-foreground flex items-center gap-2">
            <Truck className="h-5 w-5 text-primary" />
            {shipment.shipment_id}
          </SheetTitle>
          <div className="flex items-center gap-2 mt-1">
            <Badge
              variant={isDelayed ? "destructive" : "outline"}
              className="text-xs"
            >
              {STATUS_LABELS[shipment.status] || shipment.status}
            </Badge>
            <Badge
              variant="outline"
              className={cn(
                "text-xs",
                getRiskColor(shipment.delay_risk)
              )}
            >
              Risk: {Math.round(shipment.delay_risk * 100)}% {getRiskLabel(shipment.delay_risk)}
            </Badge>
          </div>
        </SheetHeader>

        {/* Route Info */}
        <div className="mt-6 space-y-5">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm">
              <MapPin className="h-4 w-4 text-emerald-400" />
              <span className="text-foreground font-medium">{shipment.origin}</span>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <div className="flex items-center gap-2 text-sm">
              <MapPin className="h-4 w-4 text-red-400" />
              <span className="text-foreground font-medium">{shipment.destination}</span>
            </div>
          </div>

          {/* Timeline */}
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-3 font-semibold">
              Journey Timeline
            </p>
            <div className="flex items-center gap-0">
              {STATUS_STEPS.map((step, i) => {
                const isCompleted = currentStepIdx >= i && !isDelayed
                const isCurrent =
                  (currentStepIdx === i && !isDelayed) ||
                  (isDelayed && step === "in_transit")
                return (
                  <div key={step} className="flex items-center flex-1">
                    <div className="flex flex-col items-center">
                      <div
                        className={cn(
                          "h-7 w-7 rounded-full flex items-center justify-center border text-[10px] font-bold",
                          isCompleted
                            ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400"
                            : isCurrent && isDelayed
                            ? "bg-red-500/20 border-red-500/40 text-red-400"
                            : isCurrent
                            ? "bg-primary/20 border-primary/40 text-primary animate-pulse"
                            : "bg-muted border-muted-foreground/20 text-muted-foreground"
                        )}
                      >
                        {isCompleted ? (
                          <CheckCircle className="h-3.5 w-3.5" />
                        ) : isCurrent && isDelayed ? (
                          <AlertTriangle className="h-3.5 w-3.5" />
                        ) : (
                          i + 1
                        )}
                      </div>
                      <span
                        className={cn(
                          "text-[9px] mt-1",
                          isCompleted || isCurrent
                            ? "text-foreground"
                            : "text-muted-foreground"
                        )}
                      >
                        {STATUS_LABELS[step]}
                      </span>
                    </div>
                    {i < STATUS_STEPS.length - 1 && (
                      <div
                        className={cn(
                          "flex-1 h-0.5 mx-1 rounded",
                          currentStepIdx > i
                            ? "bg-emerald-500/50"
                            : "bg-muted-foreground/20"
                        )}
                      />
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-accent/50 p-3">
              <p className="text-[10px] text-muted-foreground uppercase mb-1">Carrier</p>
              <p className="text-sm font-semibold text-foreground">{shipment.carrier_id}</p>
            </div>
            <div className="rounded-lg bg-accent/50 p-3">
              <p className="text-[10px] text-muted-foreground uppercase mb-1">Delay Risk</p>
              <p className={cn("text-sm font-semibold", getRiskColor(shipment.delay_risk))}>
                {Math.round(shipment.delay_risk * 100)}%
              </p>
            </div>
            <div className="rounded-lg bg-accent/50 p-3">
              <div className="flex items-center gap-1 mb-1">
                <Clock className="h-3 w-3 text-muted-foreground" />
                <p className="text-[10px] text-muted-foreground uppercase">ETA</p>
              </div>
              <p className="text-xs font-medium text-foreground">{formatTimestamp(shipment.eta)}</p>
            </div>
            <div className={cn("rounded-lg p-3", willBreachSla ? "bg-red-500/10" : "bg-accent/50")}>
              <div className="flex items-center gap-1 mb-1">
                {willBreachSla && <AlertTriangle className="h-3 w-3 text-red-400" />}
                <p className="text-[10px] text-muted-foreground uppercase">SLA Deadline</p>
              </div>
              <p className={cn("text-xs font-medium", willBreachSla ? "text-red-400" : "text-foreground")}>
                {formatTimestamp(shipment.sla_deadline)}
              </p>
            </div>
          </div>

          {/* Recommended Action */}
          {shipment.recommended_action && (
            <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1 font-semibold flex items-center gap-1">
                <AlertTriangle className="h-3 w-3 text-primary" />
                AI Recommended Action
              </p>
              <p className="text-sm text-primary font-medium">{shipment.recommended_action}</p>
            </div>
          )}

          {/* Risk Gauge */}
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-2 font-semibold">
              Risk Assessment
            </p>
            <div className="h-3 rounded-full bg-secondary overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-1000",
                  shipment.delay_risk >= 0.7
                    ? "bg-gradient-to-r from-red-600 to-red-400"
                    : shipment.delay_risk >= 0.4
                    ? "bg-gradient-to-r from-amber-600 to-amber-400"
                    : "bg-gradient-to-r from-emerald-600 to-emerald-400"
                )}
                style={{ width: `${shipment.delay_risk * 100}%` }}
              />
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-[9px] text-muted-foreground">0%</span>
              <span className="text-[9px] text-muted-foreground">100%</span>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
