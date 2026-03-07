"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import {
  AlertTriangle,
  ArrowRightLeft,
  Brain,
  CheckCircle,
  Radio,
  Truck,
  Warehouse,
  Zap,
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

  // Generate events from at-risk/delayed shipments
  shipments
    .filter((s) => s.delay_risk >= 0.7)
    .forEach((s) => {
      events.push({
        id: `alert-${s.shipment_id}`,
        icon: AlertTriangle,
        iconColor: "text-red-400",
        message: `High risk detected: ${s.shipment_id}`,
        detail: `${s.origin} → ${s.destination} | Risk: ${Math.round(s.delay_risk * 100)}%`,
        timestamp: new Date(Date.now() - Math.random() * 600000),
        type: "alert",
      })
    })

  // Generate events from agent decisions
  decisions.slice(0, 4).forEach((d) => {
    events.push({
      id: `decision-${d.log_id}`,
      icon: Brain,
      iconColor: "text-primary",
      message: `Agent decision: ${d.action_taken}`,
      detail: `${d.shipment_id} | Confidence: ${Math.round(d.confidence * 100)}%`,
      timestamp: new Date(d.timestamp),
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
        message: `Warehouse congestion: ${w.name}`,
        detail: `Load: ${w.current_load}/${w.capacity} | Queue: ${w.queue_length}`,
        timestamp: new Date(Date.now() - Math.random() * 300000),
        type: "alert",
      })
    })

  // Add some resolved actions
  events.push({
    id: "resolve-1",
    icon: CheckCircle,
    iconColor: "text-emerald-400",
    message: "Shipment SHP-1005 on schedule",
    detail: "Pune → Ahmedabad | Risk normalized to 22%",
    timestamp: new Date(Date.now() - 180000),
    type: "success",
  })

  events.push({
    id: "reroute-1",
    icon: ArrowRightLeft,
    iconColor: "text-primary",
    message: "Agent rerouted SHP-1006",
    detail: "Now using Pune corridor to avoid Mumbai congestion",
    timestamp: new Date(Date.now() - 120000),
    type: "action",
  })

  events.push({
    id: "carrier-watch",
    icon: Truck,
    iconColor: "text-amber-400",
    message: "Carrier DTDC under monitoring",
    detail: "Reliability: 44% | 3 shipments affected",
    timestamp: new Date(Date.now() - 60000),
    type: "alert",
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

  useEffect(() => {
    setEvents(generateEvents(shipments, decisions, warehouses))
  }, [shipments, decisions, warehouses])

  // Simulate new events arriving periodically
  useEffect(() => {
    const messages = [
      { icon: Radio, iconColor: "text-primary", message: "Agent polling network signals...", detail: "Observation cycle #847", type: "info" as const },
      { icon: Zap, iconColor: "text-primary", message: "Running risk inference pass", detail: "12 shipments evaluated", type: "info" as const },
      { icon: Brain, iconColor: "text-purple-400", message: "Agent reasoning: evaluating carrier switch", detail: "SHP-1003 | Comparing BlueDart vs DTDC", type: "action" as const },
      { icon: CheckCircle, iconColor: "text-emerald-400", message: "Risk threshold check passed", detail: "4 of 12 shipments within SLA", type: "success" as const },
    ]

    let idx = 0
    const timer = setInterval(() => {
      const template = messages[idx % messages.length]
      const newEvent: ActivityEvent = {
        ...template,
        id: `live-${Date.now()}`,
        timestamp: new Date(),
      }
      setEvents((prev) => [newEvent, ...prev].slice(0, 20))
      setNewEventId(newEvent.id)
      idx++
    }, 8000)

    return () => clearInterval(timer)
  }, [])

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
