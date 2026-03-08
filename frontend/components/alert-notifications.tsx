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
    // Delayed / failed shipments
    shipments
      .filter((s) => s.status === "delayed" || s.status === "failed")
      .forEach((s) => {
        const key = `ship-${s.shipment_id}`
        if (!firedRef.current.has(key)) {
          firedRef.current.add(key)
          toast({
            title: `⚠️ ${s.status === "failed" ? "Failed" : "Delayed"}: ${s.shipment_id}`,
            description: `${s.origin} → ${s.destination} | Carrier: ${s.carrier_name || s.carrier}`,
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
            title: `🏭 Warehouse Congestion: ${w.location}`,
            description: `Load: ${w.current_load}/${w.capacity} | Congestion: ${Math.round(w.congestion_score * 100)}%`,
          })
        }
      })
  }, [shipments, warehouses, toast])

  return null
}
