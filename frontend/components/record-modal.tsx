"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { X, Save, CheckCircle } from "lucide-react"
import { supabase, type TonnageRecord } from "@/lib/supabase"
import { format } from "date-fns"
import { useToast } from "@/hooks/use-toast"

interface RecordModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  record?: TonnageRecord | null
  mode: "add" | "edit"
}

export default function RecordModal({ isOpen, onClose, onSuccess, record, mode }: RecordModalProps) {
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()
  const [formData, setFormData] = useState({
    Date: "",
    "Flight No.": "",
    ACM: "",
    KG: "",
    Reg: "",
    Dep: "",
    Arr: "",
    "Out/In": "",
  })

  useEffect(() => {
    if (isOpen) {
      if (mode === "edit" && record) {
        // Populate form with existing record data
        setFormData({
          Date: record.Date ? record.Date.split("T")[0] : "",
          "Flight No.": record["Flight No."] || "",
          ACM: record.ACM || "",
          KG: record.KG?.toString() || "",
          Reg: record.Reg || "",
          Dep: record.Dep || "",
          Arr: record.Arr || "",
          "Out/In": record["Out/In"] || "",
        })
      } else {
        // Reset form for add mode
        setFormData({
          Date: "",
          "Flight No.": "",
          ACM: "",
          KG: "",
          Reg: "",
          Dep: "",
          Arr: "",
          "Out/In": "",
        })
      }
    }
  }, [isOpen, mode, record])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.Date || !formData["Flight No."] || !formData.KG) {
      toast({
        variant: "destructive",
        title: "Validation Error",
        description: "Please fill in required fields: Date, Shipment ID, and KG",
      })
      return
    }

    setLoading(true)
    try {
      // Common data (shared by add & edit)
      const baseData = {
        ...formData,
        KG: Number(formData.KG),
        Year: new Date(formData.Date).getFullYear(),
        Month: format(new Date(formData.Date), "MMMM"),
        Day: format(new Date(formData.Date), "EEEE"),
      }

      if (mode === "add") {
        // Get the next available ID by finding the max ID and adding 1
        const { data: maxIdData, error: maxIdError } = await supabase
          .from("Raya-Tonnage")
          .select("id")
          .order("id", { ascending: false })
          .limit(1)

        if (maxIdError) {
          console.error("Error getting max ID:", maxIdError)
          throw maxIdError
        }

        const nextId = maxIdData && maxIdData.length > 0 ? maxIdData[0].id + 1 : 1

        const recordData = {
          id: nextId,
          ...baseData,
        }

        const { error } = await supabase.from("Raya-Tonnage").insert([recordData])
        if (error) throw error

        toast({
          variant: "success",
          title: "Success",
          description: "Record added successfully!",
        })
      } else if (mode === "edit" && record) {
        // 🔸 Do NOT overwrite the id when updating
        const recordData = { ...baseData }

        const { error } = await supabase.from("Raya-Tonnage").update(recordData).eq("id", record.id)
        if (error) throw error

        toast({
          variant: "success",
          title: "Success",
          description: "Record updated successfully!",
        })
      }

      onSuccess()
      onClose()
    } catch (error) {
      console.error("Error:", error)
      toast({
        variant: "destructive",
        title: "Error",
        description: `Failed to ${mode === "add" ? "add" : "update"} record. Please try again.`,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (!loading) {
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-card rounded-xl border border-border shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
              <CheckCircle className="h-5 w-5 text-primary" />
            </div>
            <h2 className="text-2xl font-semibold text-foreground">
              {mode === "add" ? "Add New Record" : "Edit Record"}
            </h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClose}
            disabled={loading}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Date */}
            <div className="space-y-2">
              <Label htmlFor="modal-date" className="text-sm font-medium text-foreground">
                Date <span className="text-destructive">*</span>
              </Label>
              <Input
                id="modal-date"
                type="date"
                value={formData.Date}
                onChange={(e) => setFormData({ ...formData, Date: e.target.value })}
                className="h-11"
                required
              />
            </div>

            {/* Flight No */}
            <div className="space-y-2">
              <Label htmlFor="modal-flight" className="text-sm font-medium text-foreground">
                Shipment ID <span className="text-destructive">*</span>
              </Label>
              <Input
                id="modal-flight"
                value={formData["Flight No."]}
                onChange={(e) => setFormData({ ...formData, "Flight No.": e.target.value })}
                className="h-11"
                placeholder="e.g., SH-12345"
                required
              />
            </div>

            {/* KG */}
            <div className="space-y-2">
              <Label htmlFor="modal-kg" className="text-sm font-medium text-foreground">
                KG <span className="text-destructive">*</span>
              </Label>
              <Input
                id="modal-kg"
                type="number"
                value={formData.KG}
                onChange={(e) => setFormData({ ...formData, KG: e.target.value })}
                className="h-11"
                placeholder="e.g., 1500"
                required
              />
            </div>

            {/* Departure */}
            <div className="space-y-2">
              <Label htmlFor="modal-dep" className="text-sm font-medium text-foreground">
                Origin
              </Label>
              <Input
                id="modal-dep"
                value={formData.Dep}
                onChange={(e) => setFormData({ ...formData, Dep: e.target.value })}
                className="h-11"
                placeholder="e.g., NYC"
              />
            </div>

            {/* Arrival */}
            <div className="space-y-2">
              <Label htmlFor="modal-arr" className="text-sm font-medium text-foreground">
                Destination
              </Label>
              <Input
                id="modal-arr"
                value={formData.Arr}
                onChange={(e) => setFormData({ ...formData, Arr: e.target.value })}
                className="h-11"
                placeholder="e.g., LAX"
              />
            </div>

            {/* Out/In */}
            <div className="space-y-2">
              <Label htmlFor="modal-outin" className="text-sm font-medium text-foreground">
                Out/In
              </Label>
              <select
                id="modal-outin"
                value={formData["Out/In"]}
                onChange={(e) => setFormData({ ...formData, "Out/In": e.target.value })}
                className="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">Select...</option>
                <option value="OUT">OUT</option>
                <option value="IN">IN</option>
              </select>
            </div>

            {/* ACM */}
            <div className="space-y-2">
              <Label htmlFor="modal-acm" className="text-sm font-medium text-foreground">
                Vehicle Type
              </Label>
              <Input
                id="modal-acm"
                value={formData.ACM}
                onChange={(e) => setFormData({ ...formData, ACM: e.target.value })}
                className="h-11"
                placeholder="e.g., Truck, Rail, Ship"
              />
            </div>

            {/* Registration */}
            <div className="space-y-2">
              <Label htmlFor="modal-reg" className="text-sm font-medium text-foreground">
                Vehicle ID
              </Label>
              <Input
                id="modal-reg"
                value={formData.Reg}
                onChange={(e) => setFormData({ ...formData, Reg: e.target.value })}
                className="h-11"
                placeholder="e.g., VH-001"
              />
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 mt-8 pt-6 border-t border-border">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={loading}
              className="px-6 bg-transparent"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading} className="px-6">
              <Save className="h-4 w-4 mr-2" />
              {loading
                ? mode === "add"
                  ? "Adding..."
                  : "Updating..."
                : mode === "add"
                  ? "Add Record"
                  : "Update Record"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
