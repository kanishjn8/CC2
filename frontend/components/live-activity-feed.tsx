"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import {
  AlertTriangle,
  Brain,
  Truck,
  Warehouse,
} from "lucide-react"
import { useShipments, useDecisions, useWarehouses } from "@/hooks/use-data"
import type { LucideIcon } from "lucide-react"

interface ActivityEvent {
  id: string
  icon: LucideIcon
  iconColor: string
  message: string
  detail: string
  timestamp: Date
  type: "alert" | "action" | "info" | "success"
}

function generateEvents(
  shipments: ReturnType<typeof useShipments>["data"],
  decisions: ReturnType<typeof useDecisions>["data"],
  warehouses: ReturnType<typeof useWarehouses>["data"]
): ActivityEvent[] {
  const events: ActivityEvent[] = []

  const toUtcDate = (ts: string | null | undefined): Date =>
    ts ? new Date(ts.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(ts) ? ts : ts + "Z") : new Date()

  // Generate events from delayed/failed shipments
  shipments
    .filter((s) => s.status === "delayed" || s.status === "failed")
    .forEach((s) => {
      events.push({
        id: `alert-${s.shipment_id}`,
        icon: AlertTriangle,
        iconColor: "text-red-400",
        message: `${s.status === "failed" ? "Failed" : "Delayed"}: ${s.shipment_id}`,
        detail: `${s.origin} → ${s.destination} | Carrier: ${s.carrier_name || s.carrier}`,
        timestamp: toUtcDate(s.updated_at),
        type: "alert",
      })
    })

  // Generate events from agent decisions
  decisions.slice(0, 6).forEach((d) => {
    events.push({
      id: `decision-${d.decision_id}`,
      icon: Brain,
      iconColor: "text-primary",
      message: `Agent: ${d.recommended_action}`,
      detail: `${d.entity_id} | Confidence: ${Math.round(d.confidence * 100)}%`,
      timestamp: toUtcDate(d.created_at),
      type: "action",
    })
  })

  // Generate events from congested warehouses
  warehouses
    .filter((w) => w.congestion_score >= 0.8)
    .forEach((w) => {
      events.push({
        id: `wh-${w.warehouse_id}`,
        icon: Warehouse,
        iconColor: "text-amber-400",
        message: `Warehouse congestion: ${w.location}`,
        detail: `Load: ${w.current_load}/${w.capacity} | Queue: ${w.queue_length}`,
        timestamp: toUtcDate(w.updated_at),
        type: "alert",
      })
    })

  // Generate events from shipments with SLA breach
  shipments
    .filter((s) => s.status !== "delivered" && new Date(s.eta) > new Date(s.sla_deadline))
    .slice(0, 3)
    .forEach((s) => {
      events.push({
        id: `sla-${s.shipment_id}`,
        icon: Truck,
        iconColor: "text-amber-400",
        message: `SLA breach risk: ${s.shipment_id}`,
        detail: `${s.origin} → ${s.destination} | ETA past deadline`,
        timestamp: new Date(s.updated_at ? (s.updated_at.endsWith("Z") ? s.updated_at : s.updated_at + "Z") : Date.now()),
        type: "alert",
      })
    })

  // Sort by timestamp descending
  events.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  return events.slice(0, 15)
}

function formatTime(date: Date): string {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export function LiveActivityFeed() {
  const { data: shipments } = useShipments()
  const { data: decisions } = useDecisions()
  const { data: warehouses } = useWarehouses()
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [newEventId, setNewEventId] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Re-generate events when data changes
  useEffect(() => {
    setEvents(generateEvents(shipments, decisions, warehouses))
  }, [shipments, decisions, warehouses])

  const typeBorderColor = {
    alert: "border-l-red-500/60",
    action: "border-l-primary/60",
    info: "border-l-muted-foreground/30",
    success: "border-l-emerald-500/60",
  }

  return (
    <div ref={scrollRef} className="space-y-1 max-h-[320px] overflow-y-auto scrollbar-thin pr-1">
      <AnimatePresence initial={false}>
        {events.map((event) => {
          const Icon = event.icon
          return (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, x: -16, height: 0 }}
              animate={{ opacity: 1, x: 0, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className={cn(
                "flex items-start gap-2.5 px-3 py-2 rounded-md border-l-2 transition-colors",
                typeBorderColor[event.type],
                newEventId === event.id && "bg-primary/5"
              )}
            >
              <Icon className={cn("h-3.5 w-3.5 mt-0.5 shrink-0", event.iconColor)} />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-foreground truncate">{event.message}</p>
                <p className="text-[10px] text-muted-foreground truncate">{event.detail}</p>
              </div>
              <span className="text-[9px] text-muted-foreground/60 whitespace-nowrap mt-0.5">
                {formatTime(event.timestamp)}
              </span>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
