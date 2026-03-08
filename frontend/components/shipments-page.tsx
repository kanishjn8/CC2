"use client"

import { useState, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Search, ArrowUpDown, AlertTriangle } from "lucide-react"
import { useShipments } from "@/hooks/use-data"
import { cn, formatTimestamp } from "@/lib/utils"
import type { Shipment, ShipmentStatus } from "@/lib/types"
import { ShipmentDrawer } from "@/components/shipment-drawer"

const STATUS_LABELS: Record<ShipmentStatus, { label: string; variant: string }> = {
  created: { label: "Created", variant: "outline" },
  dispatched: { label: "Dispatched", variant: "outline" },
  in_transit: { label: "In Transit", variant: "secondary" },
  at_warehouse: { label: "At Warehouse", variant: "secondary" },
  out_for_delivery: { label: "Out for Delivery", variant: "secondary" },
  delivered: { label: "Delivered", variant: "default" },
  delayed: { label: "Delayed", variant: "destructive" },
  failed: { label: "Failed", variant: "destructive" },
}

export default function ShipmentsPage() {
  const { data: shipments, loading } = useShipments()
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [slaFilter, setSlaFilter] = useState<string>("all")
  const [sortBy, setSortBy] = useState<"eta" | "sla_deadline">("eta")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null)

  const isSlaBreaching = (s: Shipment) =>
    s.status !== "delivered" && new Date(s.eta) > new Date(s.sla_deadline)

  const filtered = useMemo(() => {
    let result = [...shipments]

    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (s) =>
          s.shipment_id.toLowerCase().includes(q) ||
          s.origin.toLowerCase().includes(q) ||
          s.destination.toLowerCase().includes(q) ||
          s.carrier.toLowerCase().includes(q)
      )
    }

    if (statusFilter !== "all") {
      result = result.filter((s) => s.status === statusFilter)
    }

    if (slaFilter === "breaching") result = result.filter((s) => isSlaBreaching(s))
    else if (slaFilter === "on_track") result = result.filter((s) => !isSlaBreaching(s))

    result.sort((a, b) => {
      const valA = new Date(sortBy === "eta" ? a.eta : a.sla_deadline).getTime()
      const valB = new Date(sortBy === "eta" ? b.eta : b.sla_deadline).getTime()
      return sortDir === "desc" ? valB - valA : valA - valB
    })

    return result
  }, [shipments, searchQuery, statusFilter, slaFilter, sortBy, sortDir])

  const toggleSort = (field: "eta" | "sla_deadline") => {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortBy(field)
      setSortDir("asc")
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  const delayedCount = shipments.filter((s) => s.status === "delayed" || s.status === "failed").length
  const breachingCount = shipments.filter((s) => isSlaBreaching(s)).length

  return (
    <div className="space-y-6">
      {/* Summary badges */}
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant="outline" className="bg-card px-3 py-1.5 text-sm">
          Total: {shipments.length}
        </Badge>
        {delayedCount > 0 && (
          <Badge variant="destructive" className="px-3 py-1.5 text-sm">
            <AlertTriangle className="h-3 w-3 mr-1" />
            Delayed/Failed: {delayedCount}
          </Badge>
        )}
        {breachingCount > 0 && (
          <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30 px-3 py-1.5 text-sm">
            SLA Breaching: {breachingCount}
          </Badge>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search shipments, origins, destinations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="in_transit">In Transit</SelectItem>
                <SelectItem value="dispatched">Dispatched</SelectItem>
                <SelectItem value="at_risk">At Risk</SelectItem>
                <SelectItem value="delayed">Delayed</SelectItem>
                <SelectItem value="delivered">Delivered</SelectItem>
              </SelectContent>
            </Select>
            <Select value={slaFilter} onValueChange={setSlaFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="SLA Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All SLA Status</SelectItem>
                <SelectItem value="breaching">SLA Breaching</SelectItem>
                <SelectItem value="on_track">On Track</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-muted-foreground">
            Shipment Risk Explorer — {filtered.length} results
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[120px]">Shipment ID</TableHead>
                <TableHead>Origin</TableHead>
                <TableHead>Destination</TableHead>
                <TableHead>Carrier</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>ETA
                  <Button variant="ghost" size="sm" className="ml-1 h-6 w-6 p-0" onClick={() => toggleSort("eta")}>
                    <ArrowUpDown className="h-3 w-3" />
                  </Button>
                </TableHead>
                <TableHead>
                  SLA Deadline
                  <Button variant="ghost" size="sm" className="ml-1 h-6 w-6 p-0" onClick={() => toggleSort("sla_deadline")}>
                    <ArrowUpDown className="h-3 w-3" />
                  </Button>
                </TableHead>
                <TableHead>SLA Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((shipment) => {
                const statusInfo = STATUS_LABELS[shipment.status]
                const breaching = isSlaBreaching(shipment)
                return (
                  <TableRow
                    key={shipment.shipment_id}
                    className={cn(
                      "cursor-pointer transition-colors hover:bg-accent/50",
                      breaching && "bg-red-500/5"
                    )}
                    onClick={() => setSelectedShipment(shipment)}
                  >
                    <TableCell className="font-mono font-semibold text-foreground">
                      {shipment.shipment_id}
                    </TableCell>
                    <TableCell>{shipment.origin}</TableCell>
                    <TableCell>{shipment.destination}</TableCell>
                    <TableCell className="text-muted-foreground">{shipment.carrier_name || shipment.carrier}</TableCell>
                    <TableCell>
                      <Badge
                        variant={statusInfo?.variant as "default" | "outline" | "secondary" | "destructive" ?? "outline"}
                        className="text-xs"
                      >
                        {statusInfo?.label || shipment.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatTimestamp(shipment.eta)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatTimestamp(shipment.sla_deadline)}
                    </TableCell>
                    <TableCell>
                      {shipment.status === "delivered" ? (
                        <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                          Delivered
                        </Badge>
                      ) : breaching ? (
                        <Badge variant="destructive" className="text-[10px]">
                          <AlertTriangle className="h-2.5 w-2.5 mr-1" />
                          Breaching
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                          On Track
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    No shipments match your filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <ShipmentDrawer
        shipment={selectedShipment}
        open={!!selectedShipment}
        onClose={() => setSelectedShipment(null)}
      />
    </div>
  )
}
