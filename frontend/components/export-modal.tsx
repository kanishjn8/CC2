"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { X, Download, FileText, Table } from "lucide-react"
import type { TonnageRecord } from "@/lib/supabase"
import { format } from "date-fns"

interface ExportModalProps {
  isOpen: boolean
  onClose: () => void
  data: TonnageRecord[]
  filteredCount: number
  totalCount: number
}

export default function ExportModal({ isOpen, onClose, data, filteredCount, totalCount }: ExportModalProps) {
  const [loading, setLoading] = useState(false)
  const [exportFormat, setExportFormat] = useState<"csv" | "xlsx">("csv")

  const handleExport = async (exportFormat: "csv" | "xlsx") => {
    setLoading(true)
    try {
      const exportData = data.map((record) => ({
        ID: record.id,
        Date: record.Date ? format(new Date(record.Date), "yyyy-MM-dd") : "",
        "Shipment ID": record["Flight No."] || "",
        "Vehicle Type": record.ACM || "",
        KG: record.KG || 0,
        "Vehicle ID": record.Reg || "",
        Month: record.Month || "",
        Year: record.Year || "",
        Day: record.Day || "",
        Sector: record.Sector || "",
        Origin: record.Dep || "",
        Destination: record.Arr || "",
        "Out/In": record["Out/In"] || "",
        Station: record.Station || "",
        "Dom/Int": record["Dom/Int"] || "",
      }))

      const currentDate = format(new Date(), "yyyy-MM-dd")

      if (exportFormat === "csv") {
        // Generate CSV
        const headers = Object.keys(exportData[0] || {})
        const csvContent = [
          headers.join(","),
          ...exportData.map((row) =>
            headers
              .map((header) => {
                const value = row[header as keyof typeof row]
                // Escape commas and quotes in CSV
                if (typeof value === "string" && (value.includes(",") || value.includes('"'))) {
                  return `"${value.replace(/"/g, '""')}"`
                }
                return value
              })
              .join(","),
          ),
        ].join("\n")

        // Download CSV
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
        const link = document.createElement("a")
        const url = URL.createObjectURL(blob)
        link.setAttribute("href", url)
        link.setAttribute("download", `tonnage-report-${currentDate}.csv`)
        link.style.visibility = "hidden"
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
      } else {
        // Generate XLSX using browser-compatible approach
        try {
          const XLSX = await import("xlsx")

          // Create worksheet from JSON data
          const worksheet = XLSX.utils.json_to_sheet(exportData)

          // Create workbook and add worksheet
          const workbook = XLSX.utils.book_new()
          XLSX.utils.book_append_sheet(workbook, worksheet, "Tonnage Report")

          // Set column widths
          const colWidths = Object.keys(exportData[0] || {}).map((key) => ({
            wch: Math.max(key.length, 15),
          }))
          worksheet["!cols"] = colWidths

          // Generate buffer and create blob
          const excelBuffer = XLSX.write(workbook, {
            bookType: "xlsx",
            type: "array",
            compression: true,
          })

          const blob = new Blob([excelBuffer], {
            type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          })

          // Download file
          const link = document.createElement("a")
          const url = URL.createObjectURL(blob)
          link.setAttribute("href", url)
          link.setAttribute("download", `tonnage-report-${currentDate}.xlsx`)
          link.style.visibility = "hidden"
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          URL.revokeObjectURL(url)
        } catch (xlsxError) {
          console.error("XLSX export error:", xlsxError)
          // Fallback to CSV if XLSX fails
          alert("Excel export failed. Downloading as CSV instead.")
          await handleExport("csv")
          return
        }
      }

      onClose()
    } catch (error) {
      console.error("Export error:", error)
      alert("Failed to export data. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-card rounded-xl border border-border shadow-2xl w-full max-w-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-900/30 rounded-lg border border-green-700/50">
              <Download className="h-5 w-5 text-green-400" />
            </div>
            <h2 className="text-2xl font-semibold text-foreground">Export Tonnage Data</h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={loading}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Export Summary */}
          <div className="bg-muted/30 rounded-lg p-4 border border-border">
            <h3 className="text-lg font-medium text-foreground mb-3">Export Summary</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Records to Export</p>
                <p className="text-2xl font-bold text-foreground">{filteredCount.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Available</p>
                <p className="text-2xl font-bold text-muted-foreground">{totalCount.toLocaleString()}</p>
              </div>
            </div>
            {filteredCount < totalCount && (
              <div className="mt-3 p-3 bg-primary/10 rounded-md border border-primary/20">
                <p className="text-sm text-primary">
                  <strong>Note:</strong> Only filtered data will be exported. Clear filters to export all records.
                </p>
              </div>
            )}
          </div>

          {/* Format Selection */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-foreground">Choose Export Format</h3>
            <div className="grid grid-cols-2 gap-4">
              {/* CSV Option */}
              <div
                className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  exportFormat === "csv"
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card hover:border-primary/50"
                }`}
                onClick={() => setExportFormat("csv")}
              >
                <div className="flex items-center gap-3 mb-2">
                  <FileText className="h-5 w-5 text-primary" />
                  <span className="font-medium text-foreground">CSV Format</span>
                  {exportFormat === "csv" && (
                    <Badge variant="secondary" className="bg-primary/20 text-primary border-primary/50">
                      Selected
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  Comma-separated values. Compatible with Excel, Google Sheets, and most data tools.
                </p>
              </div>

              {/* XLSX Option */}
              <div
                className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  exportFormat === "xlsx"
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card hover:border-primary/50"
                }`}
                onClick={() => setExportFormat("xlsx")}
              >
                <div className="flex items-center gap-3 mb-2">
                  <Table className="h-5 w-5 text-primary" />
                  <span className="font-medium text-foreground">Excel Format</span>
                  {exportFormat === "xlsx" && (
                    <Badge variant="secondary" className="bg-primary/20 text-primary border-primary/50">
                      Selected
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  Native Excel format with auto-sized columns. Best for advanced Excel features.
                </p>
              </div>
            </div>
          </div>

          {/* Data Preview */}
          <div className="space-y-3">
            <h3 className="text-lg font-medium text-foreground">Data Preview</h3>
            <div className="bg-muted/30 rounded-lg p-4 border border-border">
              <p className="text-sm text-muted-foreground mb-2">Columns included in export:</p>
              <div className="flex flex-wrap gap-2">
                {[
                  "ID",
                  "Date",
                  "Shipment ID",
                  "Vehicle Type",
                  "KG",
                  "Vehicle ID",
                  "Month",
                  "Year",
                  "Day",
                  "Sector",
                  "Origin",
                  "Destination",
                  "Out/In",
                  "Station",
                  "Dom/Int",
                ].map((column) => (
                  <Badge key={column} variant="outline" className="text-xs">
                    {column}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-border">
          <Button variant="outline" onClick={onClose} disabled={loading} className="px-6 bg-transparent">
            Cancel
          </Button>
          <Button onClick={() => handleExport(exportFormat)} disabled={loading || filteredCount === 0} className="px-6">
            <Download className="h-4 w-4 mr-2" />
            {loading
              ? "Exporting..."
              : `Export ${exportFormat.toUpperCase()} (${filteredCount.toLocaleString()} records)`}
          </Button>
        </div>
      </div>
    </div>
  )
}
