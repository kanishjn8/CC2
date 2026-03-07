"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Plus, Trash2, Database, RefreshCw, Edit, AlertTriangle } from "lucide-react"
import { supabase, type TonnageRecord } from "@/lib/supabase"
import { format } from "date-fns"
import RecordModal from "./record-modal"
import { useToast } from "@/hooks/use-toast"

export default function DataManagement() {
  const [data, setData] = useState<TonnageRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [showDeleteMode, setShowDeleteMode] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<"add" | "edit">("add")
  const [selectedRecord, setSelectedRecord] = useState<TonnageRecord | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    fetchTonnageData()
  }, [])

  const fetchTonnageData = async () => {
    try {
      setLoading(true)
      const { data: tonnageData, error } = await supabase
        .from("Raya-Tonnage")
        .select("*")
        .order("Date", { ascending: false })

      if (error) {
        console.error("Error fetching data:", error)
        toast({
          variant: "destructive",
          title: "Error",
          description: "Failed to fetch tonnage data. Please try again.",
        })
        return
      }

      setData(tonnageData || [])
    } catch (error) {
      console.error("Error:", error)
      toast({
        variant: "destructive",
        title: "Error",
        description: "An unexpected error occurred while fetching data.",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteRecord = async (id: number) => {
    const record = data.find((r) => r.id === id)
    const confirmMessage = `Are you sure you want to delete this record?\n\nShipment: ${record?.["Flight No."] || "N/A"}\nDate: ${record?.Date ? format(new Date(record.Date), "MMM d, yyyy") : "N/A"}`

    if (!confirm(confirmMessage)) return

    setActionLoading(true)
    try {
      const { error } = await supabase.from("Raya-Tonnage").delete().eq("id", id)

      if (error) {
        console.error("Error deleting record:", error)
        toast({
          variant: "destructive",
          title: "Delete Failed",
          description: "Failed to delete record. Please try again.",
        })
        return
      }

      toast({
        variant: "success",
        title: "Success",
        description: "Record deleted successfully!",
      })
      fetchTonnageData()
    } catch (error) {
      console.error("Error:", error)
      toast({
        variant: "destructive",
        title: "Error",
        description: "An unexpected error occurred while deleting the record.",
      })
    } finally {
      setActionLoading(false)
    }
  }

  const openAddModal = () => {
    setModalMode("add")
    setSelectedRecord(null)
    setModalOpen(true)
  }

  const openEditModal = (record: TonnageRecord) => {
    setModalMode("edit")
    setSelectedRecord(record)
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setSelectedRecord(null)
  }

  const handleModalSuccess = () => {
    fetchTonnageData()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <div className="space-y-2">
            <p className="text-lg font-medium text-foreground">Loading Data</p>
            <p className="text-sm text-muted-foreground">Fetching tonnage records...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-border bg-card hover:bg-accent/5 transition-colors">
          <CardContent className="p-6 flex flex-col justify-center min-h-[120px]">
            <div className="flex items-center space-x-4">
              <div className="p-1.5 bg-primary/10 rounded-md border border-primary/20">
                <Database className="h-4 w-4 text-primary" />
              </div>
              <div className="text-2xl font-bold text-foreground">{data.length.toLocaleString()}</div>
            </div>
            <CardTitle className="text-sm font-medium text-muted-foreground mt-3">Total Records</CardTitle>
          </CardContent>
        </Card>

        <Card className="border-border bg-card hover:bg-accent/5 transition-colors">
          <CardContent className="p-6 flex flex-col justify-center min-h-[120px]">
            <div className="flex items-center space-x-4">
              <div className="p-1.5 bg-blue-900/30 rounded-md border border-blue-700/50">
                <Database className="h-4 w-4 text-blue-500" />
              </div>
              <div className="text-2xl font-bold text-foreground">
                {data.reduce((sum, item) => sum + (item.KG || 0), 0).toLocaleString()} kg
              </div>
            </div>
            <CardTitle className="text-sm font-medium text-muted-foreground mt-3">Total Tonnage</CardTitle>
          </CardContent>
        </Card>

        <Card className="border-border bg-card hover:bg-accent/5 transition-colors">
          <CardContent className="p-6 flex flex-col justify-center min-h-[120px]">
            <div className="flex items-center space-x-4">
              <div className="p-1.5 bg-green-900/30 rounded-md border border-green-700/50">
                <Database className="h-4 w-4 text-green-500" />
              </div>
              <div className="text-2xl font-bold text-foreground">
                {data[0]?.Date ? format(new Date(data[0].Date), "MMM d") : "N/A"}
              </div>
            </div>
            <CardTitle className="text-sm font-medium text-muted-foreground mt-3">Latest Record</CardTitle>
          </CardContent>
        </Card>
      </div>

      {/* Main Data Management Card */}
      <Card className="border-border bg-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
                <Database className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-foreground">Tonnage Records Management</CardTitle>
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={fetchTonnageData} disabled={loading}>
                <RefreshCw className="h-4 w-4 mr-1" />
                Refresh
              </Button>
              <Button size="sm" onClick={openAddModal}>
                <Plus className="h-4 w-4 mr-1" />
                Add Record
              </Button>
              <Button
                size="sm"
                variant={showDeleteMode ? "destructive" : "outline"}
                onClick={() => setShowDeleteMode(!showDeleteMode)}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                {showDeleteMode ? "Cancel Delete" : "Delete Mode"}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Delete Mode Warning */}
          {showDeleteMode && (
            <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
              <AlertTriangle className="h-4 w-4 text-destructive" />
              <p className="text-sm text-destructive font-medium">
                Delete mode is active. Click the delete button next to any record to remove it permanently.
              </p>
            </div>
          )}

          {/* Records Table */}
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="p-4 border-b border-border bg-muted/30">
              <h3 className="text-lg font-medium text-foreground">All Records</h3>
              <p className="text-sm text-muted-foreground">{data.length} total records (showing most recent first)</p>
            </div>
            <div className="overflow-x-auto max-h-96">
              <table className="w-full">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Shipment
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Route
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      KG
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Direction
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Vehicle Type
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Vehicle ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.map((record) => (
                    <tr key={record.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {record.Date ? format(new Date(record.Date), "MMM d, yyyy") : "N/A"}
                      </td>
                      <td className="px-4 py-3 text-sm text-foreground font-medium">{record["Flight No."] || "N/A"}</td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {record.Dep && record.Arr ? `${record.Dep} → ${record.Arr}` : "N/A"}
                      </td>
                      <td className="px-4 py-3 text-sm text-foreground font-medium">
                        {record.KG?.toLocaleString() || 0} kg
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <Badge
                          variant={
                            record["Out/In"] === "OUT" ? "default" : record["Out/In"] === "IN" ? "secondary" : "outline"
                          }
                        >
                          {record["Out/In"] || "N/A"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{record.ACM || "N/A"}</td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">{record.Reg || "N/A"}</td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openEditModal(record)}
                            disabled={actionLoading}
                            className="h-8 px-2"
                          >
                            <Edit className="h-3 w-3" />
                          </Button>
                          {showDeleteMode && (
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleDeleteRecord(record.id)}
                              disabled={actionLoading}
                              className="h-8 px-2"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Record Modal */}
      <RecordModal
        isOpen={modalOpen}
        onClose={closeModal}
        onSuccess={handleModalSuccess}
        record={selectedRecord}
        mode={modalMode}
      />
    </div>
  )
}
