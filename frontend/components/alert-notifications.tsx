"use client"

import { useEffect, useRef } from "react"
import { useShipments, useWarehouses } from "@/hooks/use-data"
import { useToast } from "@/hooks/use-toast"

/**
 * Watches for threshold breaches and fires toast notifications.
 * Mount once in layout — it auto-polls via hooks.
 */
export function AlertNotifications() {
  const { data: shipments } = useShipments()
  const { data: warehouses } = useWarehouses()
  const { toast } = useToast()
  const firedRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    // High-risk shipments
    shipments
      .filter((s) => s.delay_risk >= 0.85)
      .forEach((s) => {
        const key = `ship-${s.shipment_id}`
        if (!firedRef.current.has(key)) {
          firedRef.current.add(key)
          toast({
            title: `⚠️ Critical Risk: ${s.shipment_id}`,
            description: `${s.origin} → ${s.destination} | Delay risk ${Math.round(s.delay_risk * 100)}%`,
            variant: "destructive",
          })
        }
      })

    // Congested warehouses
    warehouses
      .filter((w) => w.congestion_score >= 0.9)
      .forEach((w) => {
        const key = `wh-${w.warehouse_id}`
        if (!firedRef.current.has(key)) {
          firedRef.current.add(key)
          toast({
            title: `🏭 Warehouse Congestion: ${w.name}`,
            description: `Load: ${w.current_load}/${w.capacity} | Congestion: ${Math.round(w.congestion_score * 100)}%`,
          })
        }
      })
  }, [shipments, warehouses, toast])

  return null
}
