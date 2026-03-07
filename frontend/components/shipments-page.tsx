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
import { cn, getRiskColor, getRiskLabel, getRiskBg, formatTimestamp } from "@/lib/utils"
import type { Shipment, ShipmentStatus } from "@/lib/types"
import { ShipmentDrawer } from "@/components/shipment-drawer"

const STATUS_LABELS: Record<ShipmentStatus, { label: string; variant: string }> = {
  created: { label: "Created", variant: "outline" },
  dispatched: { label: "Dispatched", variant: "outline" },
  in_transit: { label: "In Transit", variant: "secondary" },
  delivered: { label: "Delivered", variant: "default" },
  delayed: { label: "Delayed", variant: "destructive" },
  at_risk: { label: "At Risk", variant: "destructive" },
}

export default function ShipmentsPage() {
  const { data: shipments, loading } = useShipments()
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [riskFilter, setRiskFilter] = useState<string>("all")
  const [sortBy, setSortBy] = useState<"delay_risk" | "eta">("delay_risk")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null)

  const filtered = useMemo(() => {
    let result = [...shipments]

    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (s) =>
          s.shipment_id.toLowerCase().includes(q) ||
          s.origin.toLowerCase().includes(q) ||
          s.destination.toLowerCase().includes(q) ||
          s.carrier_id.toLowerCase().includes(q)
      )
    }

    if (statusFilter !== "all") {
      result = result.filter((s) => s.status === statusFilter)
    }

    if (riskFilter === "critical") result = result.filter((s) => s.delay_risk >= 0.7)
    else if (riskFilter === "warning") result = result.filter((s) => s.delay_risk >= 0.4 && s.delay_risk < 0.7)
    else if (riskFilter === "normal") result = result.filter((s) => s.delay_risk < 0.4)

    result.sort((a, b) => {
      const valA = sortBy === "delay_risk" ? a.delay_risk : new Date(a.eta).getTime()
      const valB = sortBy === "delay_risk" ? b.delay_risk : new Date(b.eta).getTime()
      return sortDir === "desc" ? valB - valA : valA - valB
    })

    return result
  }, [shipments, searchQuery, statusFilter, riskFilter, sortBy, sortDir])

  const toggleSort = (field: "delay_risk" | "eta") => {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortBy(field)
      setSortDir("desc")
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  const criticalCount = shipments.filter((s) => s.delay_risk >= 0.7).length
  const warningCount = shipments.filter((s) => s.delay_risk >= 0.4 && s.delay_risk < 0.7).length

  return (
    <div className="space-y-6">
      {/* Summary badges */}
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant="outline" className="bg-card px-3 py-1.5 text-sm">
          Total: {shipments.length}
        </Badge>
        <Badge variant="destructive" className="px-3 py-1.5 text-sm">
          <AlertTriangle className="h-3 w-3 mr-1" />
          Critical: {criticalCount}
        </Badge>
        <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30 px-3 py-1.5 text-sm">
          Warning: {warningCount}
        </Badge>
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
            <Select value={riskFilter} onValueChange={setRiskFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Risk Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Risk Levels</SelectItem>
                <SelectItem value="critical">Critical (&ge;70%)</SelectItem>
                <SelectItem value="warning">Warning (40-70%)</SelectItem>
                <SelectItem value="normal">Normal (&lt;40%)</SelectItem>
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
                  Delay Risk
                  <Button variant="ghost" size="sm" className="ml-1 h-6 w-6 p-0" onClick={() => toggleSort("delay_risk")}>
                    <ArrowUpDown className="h-3 w-3" />
                  </Button>
                </TableHead>
                <TableHead>Recommended Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((shipment) => {
                const statusInfo = STATUS_LABELS[shipment.status]
                return (
                  <TableRow
                    key={shipment.shipment_id}
                    className={cn(
                      "cursor-pointer transition-colors hover:bg-accent/50",
                      shipment.delay_risk >= 0.7 && "bg-red-500/5"
                    )}
                    onClick={() => setSelectedShipment(shipment)}
                  >
                    <TableCell className="font-mono font-semibold text-foreground">
                      {shipment.shipment_id}
                    </TableCell>
                    <TableCell>{shipment.origin}</TableCell>
                    <TableCell>{shipment.destination}</TableCell>
                    <TableCell className="text-muted-foreground">{shipment.carrier_id}</TableCell>
                    <TableCell>
                      <Badge
                        variant={statusInfo.variant as "default" | "outline" | "secondary" | "destructive"}
                        className="text-xs"
                      >
                        {statusInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatTimestamp(shipment.eta)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div
                          className={cn(
                            "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold",
                            getRiskBg(shipment.delay_risk),
                            getRiskColor(shipment.delay_risk)
                          )}
                        >
                          {(shipment.delay_risk * 100).toFixed(0)}%
                        </div>
                        <span className={cn("text-[10px]", getRiskColor(shipment.delay_risk))}>
                          {getRiskLabel(shipment.delay_risk)}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[200px]">
                      {shipment.recommended_action ? (
                        <span className="text-xs text-primary">
                          {shipment.recommended_action}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground/50">—</span>
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
