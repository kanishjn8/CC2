"use client"

import { useState, useEffect, useMemo } from "react"
import { Card, CardContent, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Filter, Calendar, Truck, TrendingUp, BarChart3, ChevronLeft, ChevronRight, Plus, Download } from "lucide-react"
import { FacetedFilter } from "@/components/faceted-filter"
import RouteDistributionChart from "@/components/route-distribution-chart"
import InboundOutboundTrendChart from "@/components/inbound-outbound-trend-chart"
import ShipmentTonnageStackedChart from "@/components/shipment-tonnage-stacked-chart"
import ExportModal from "@/components/export-modal"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import { Separator } from "@/components/ui/separator"
import { supabase, type TonnageRecord } from "@/lib/supabase"
import Link from "next/link"

interface Filters {
  dateFrom?: string
  dateTo?: string
  origins: Set<string>
  destinations: Set<string>
  vehicleTypes: Set<string>
  shipmentIds: Set<string>
  vehicleIds: Set<string>
}

interface DateRangePickerProps {
  dateFrom?: string
  dateTo?: string
  onDateChange: (from: string, to: string) => void
  minDate: string
  maxDate: string
}

function DateRangePicker({ dateFrom, dateTo, onDateChange, minDate, maxDate }: DateRangePickerProps) {
  const [currentMonth, setCurrentMonth] = useState(() => {
    if (dateFrom) return new Date(dateFrom)
    if (minDate) return new Date(minDate)
    return new Date()
  })

  const [selectingFrom, setSelectingFrom] = useState(true)
  const [tempFrom, setTempFrom] = useState(dateFrom || "")
  const [tempTo, setTempTo] = useState(dateTo || "")

  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ]

  const dayNames = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]

  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const daysInMonth = lastDay.getDate()
    const startingDayOfWeek = firstDay.getDay()

    const days = []

    // Previous month's trailing days
    const prevMonth = new Date(year, month - 1, 0)
    for (let i = startingDayOfWeek - 1; i >= 0; i--) {
      days.push({
        day: prevMonth.getDate() - i,
        isCurrentMonth: false,
        date: new Date(year, month - 1, prevMonth.getDate() - i),
      })
    }

    // Current month's days
    for (let day = 1; day <= daysInMonth; day++) {
      days.push({
        day,
        isCurrentMonth: true,
        date: new Date(year, month, day),
      })
    }

    // Next month's leading days
    const remainingDays = 42 - days.length
    for (let day = 1; day <= remainingDays; day++) {
      days.push({
        day,
        isCurrentMonth: false,
        date: new Date(year, month + 1, day),
      })
    }

    return days
  }

  const formatDateString = (date: Date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, "0")
    const day = String(date.getDate()).padStart(2, "0")
    return `${year}-${month}-${day}`
  }

  const isDateInRange = (date: Date) => {
    if (!tempFrom || !tempTo) return false
    const dateStr = formatDateString(date)
    return dateStr >= tempFrom && dateStr <= tempTo
  }

  const isDateSelected = (date: Date) => {
    const dateStr = formatDateString(date)
    return dateStr === tempFrom || dateStr === tempTo
  }

  const handleDateClick = (date: Date) => {
    // Use local date string to avoid timezone issues
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, "0")
    const day = String(date.getDate()).padStart(2, "0")
    const dateStr = `${year}-${month}-${day}`

    if (selectingFrom || !tempFrom) {
      setTempFrom(dateStr)
      setTempTo("")
      setSelectingFrom(false)
    } else {
      if (dateStr < tempFrom) {
        setTempTo(tempFrom)
        setTempFrom(dateStr)
      } else {
        setTempTo(dateStr)
      }
      setSelectingFrom(true)
    }
  }

  const navigateMonth = (direction: "prev" | "next") => {
    setCurrentMonth((prev) => {
      const newMonth = new Date(prev)
      if (direction === "prev") {
        newMonth.setMonth(prev.getMonth() - 1)
      } else {
        newMonth.setMonth(prev.getMonth() + 1)
      }
      return newMonth
    })
  }

  const applySelection = () => {
    onDateChange(tempFrom, tempTo)
  }

  const clearSelection = () => {
    setTempFrom("")
    setTempTo("")
    onDateChange("", "")
  }

  const days = getDaysInMonth(currentMonth)

  return (
    <div className="p-4 bg-popover rounded-lg border border-border">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigateMonth("prev")}
          className="text-muted-foreground hover:text-foreground hover:bg-accent"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <h3 className="text-lg font-semibold text-foreground">
          {monthNames[currentMonth.getMonth()]} {currentMonth.getFullYear()}
        </h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigateMonth("next")}
          className="text-muted-foreground hover:text-foreground hover:bg-accent"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {dayNames.map((day) => (
          <div key={day} className="text-center text-sm font-medium text-muted-foreground py-2">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1 mb-4">
        {days.map((dayObj, index) => {
          const isSelected = isDateSelected(dayObj.date)
          const isInRange = isDateInRange(dayObj.date)
          const isToday = formatDateString(dayObj.date) === formatDateString(new Date())

          return (
            <Button
              key={index}
              variant="ghost"
              size="sm"
              onClick={() => dayObj.isCurrentMonth && handleDateClick(dayObj.date)}
              disabled={!dayObj.isCurrentMonth}
              className={cn(
                "h-10 w-10 p-0 text-sm font-medium transition-colors",
                dayObj.isCurrentMonth ? "text-foreground hover:bg-accent" : "text-muted-foreground cursor-not-allowed",
                isSelected && "bg-primary text-primary-foreground hover:bg-primary/90",
                isInRange && !isSelected && "bg-primary/10 text-primary",
                isToday && !isSelected && "ring-1 ring-primary",
              )}
            >
              {dayObj.day}
            </Button>
          )
        })}
      </div>

      {/* Selection info and actions */}
      <div className="space-y-3 border-t border-border pt-3">
        <div className="text-sm text-muted-foreground">
          {tempFrom && tempTo ? (
            <span>
              Selected:{" "}
              {new Date(tempFrom + "T00:00:00").toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}{" "}
              -{" "}
              {new Date(tempTo + "T00:00:00").toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </span>
          ) : tempFrom ? (
            <span>
              From:{" "}
              {new Date(tempFrom + "T00:00:00").toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}{" "}
              (select end date)
            </span>
          ) : (
            <span>Select start date</span>
          )}
        </div>

        <div className="flex justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={clearSelection}
            className="text-muted-foreground border-border hover:bg-accent bg-transparent"
          >
            Clear
          </Button>
          <Button
            size="sm"
            onClick={applySelection}
            disabled={!tempFrom || !tempTo}
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            Apply
          </Button>
        </div>
      </div>
    </div>
  )
}

export default function TonnageDashboard() {
  const [data, setData] = useState<TonnageRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [exportModalOpen, setExportModalOpen] = useState(false)
  const [hasUserInteracted, setHasUserInteracted] = useState(false)
  const [filters, setFilters] = useState<Filters>({
    origins: new Set(),
    destinations: new Set(),
    vehicleTypes: new Set(),
    shipmentIds: new Set(),
    vehicleIds: new Set(),
  })

  // Calculate year-to-date range
  const getYearToDateRange = () => {
    const now = new Date()
    const currentYear = now.getFullYear()

    // Explicitly set January 1st of current year
    const startOfYear = new Date(currentYear, 0, 1) // Month 0 = January, Day 1

    // Format dates as YYYY-MM-DD strings
    const yearStart = `${currentYear}-01-01`
    const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`

    return { yearStart, today }
  }

  useEffect(() => {
    fetchTonnageData()
  }, [])

  // Set default year-to-date filter after data is loaded (but don't show in UI)
  useEffect(() => {
    if (data.length > 0 && !hasUserInteracted) {
      const { yearStart, today } = getYearToDateRange()

      // Debug: Log the YTD range being applied
      console.log("Applying YTD filter:", { yearStart, today })
      console.log("Data date range:", {
        earliest: data
          .map((item) => item.Date?.split("T")[0])
          .filter(Boolean)
          .sort()[0],
        latest: data
          .map((item) => item.Date?.split("T")[0])
          .filter(Boolean)
          .sort()
          .slice(-1)[0],
      })

      setFilters((prev) => ({
        ...prev,
        dateFrom: yearStart,
        dateTo: today,
      }))
    }
  }, [data, hasUserInteracted])

  const fetchTonnageData = async () => {
    try {
      setLoading(true)
      const { data: tonnageData, error } = await supabase
        .from("Raya-Tonnage")
        .select("*")
        .order("Date", { ascending: false })

      if (error) {
        console.error("Error fetching data:", error)
        return
      }

      setData(tonnageData || [])
    } catch (error) {
      console.error("Error:", error)
    } finally {
      setLoading(false)
    }
  }

  const filteredData = useMemo(() => {
    const filtered = data.filter((item) => {
      // Date range filter - fixed timezone handling
      if (filters.dateFrom && filters.dateFrom.trim() !== "") {
        const dateStr = item.Date?.split("T")[0]
        if (!dateStr) return false
        if (dateStr < filters.dateFrom) return false
      }

      if (filters.dateTo && filters.dateTo.trim() !== "") {
        const dateStr = item.Date?.split("T")[0]
        if (!dateStr) return false
        if (dateStr > filters.dateTo) return false
      }

      // Origin filter - robust data cleaning
      if (filters.origins.size > 0) {
        const origin = item.Dep?.toString().trim().toUpperCase()
        if (!origin) return false

        // Check if any selected origin matches (case-insensitive)
        const hasMatch = Array.from(filters.origins).some((selectedOrigin) => selectedOrigin.toUpperCase() === origin)
        if (!hasMatch) return false
      }

      // Destination filter - robust data cleaning
      if (filters.destinations.size > 0) {
        const destination = item.Arr?.toString().trim().toUpperCase()
        if (!destination) return false

        // Check if any selected destination matches (case-insensitive)
        const hasMatch = Array.from(filters.destinations).some(
          (selectedDestination) => selectedDestination.toUpperCase() === destination,
        )
        if (!hasMatch) return false
      }

      if (filters.vehicleTypes.size > 0) {
        const vehicleType = item.ACM?.toString().trim().toUpperCase()
        if (!vehicleType) return false

        const hasMatch = Array.from(filters.vehicleTypes).some(
          (selectedType) => selectedType.toUpperCase() === vehicleType,
        )
        if (!hasMatch) return false
      }

      if (filters.shipmentIds.size > 0) {
        const shipmentId = item["Flight No."]?.toString().trim().toUpperCase()
        if (!shipmentId) return false

        const hasMatch = Array.from(filters.shipmentIds).some((selectedId) => selectedId.toUpperCase() === shipmentId)
        if (!hasMatch) return false
      }

      if (filters.vehicleIds.size > 0) {
        const vehicleId = item.Reg?.toString().trim().toUpperCase()
        if (!vehicleId) return false

        const hasMatch = Array.from(filters.vehicleIds).some((selectedId) => selectedId.toUpperCase() === vehicleId)
        if (!hasMatch) return false
      }

      return true
    })

    // Debug: Log filtering results
    if (!hasUserInteracted && (filters.dateFrom || filters.dateTo)) {
      console.log("YTD Filtering Results:", {
        totalRecords: data.length,
        filteredRecords: filtered.length,
        dateRange: { from: filters.dateFrom, to: filters.dateTo },
        filteredDateRange: {
          earliest: filtered
            .map((item) => item.Date?.split("T")[0])
            .filter(Boolean)
            .sort()[0],
          latest: filtered
            .map((item) => item.Date?.split("T")[0])
            .filter(Boolean)
            .sort()
            .slice(-1)[0],
        },
      })
    }

    return filtered
  }, [data, filters, hasUserInteracted])

  const uniqueOrigins = useMemo(
    () => [...new Set(data.map((item) => item.Dep?.toString().trim().toUpperCase()).filter(Boolean))].sort(),
    [data],
  )

  const uniqueDestinations = useMemo(
    () => [...new Set(data.map((item) => item.Arr?.toString().trim().toUpperCase()).filter(Boolean))].sort(),
    [data],
  )

  const uniqueVehicleTypes = useMemo(
    () => [...new Set(data.map((item) => item.ACM?.toString().trim().toUpperCase()).filter(Boolean))].sort(),
    [data],
  )

  const uniqueShipmentIds = useMemo(
    () => [...new Set(data.map((item) => item["Flight No."]?.toString().trim().toUpperCase()).filter(Boolean))].sort(),
    [data],
  )

  const uniqueVehicleIds = useMemo(
    () => [...new Set(data.map((item) => item.Reg?.toString().trim().toUpperCase()).filter(Boolean))].sort(),
    [data],
  )

  const totalTonnage = useMemo(() => filteredData.reduce((sum, item) => sum + (item.KG || 0), 0), [filteredData])

  const totalShipments = filteredData.length

  // Calculate digit count for layout logic (excluding commas)
  const totalTonnageDigits = useMemo(() => {
    return totalTonnage.toString().replace(/,/g, "").length
  }, [totalTonnage])

  // Determine if Total Tonnage should expand (8+ digits)
  const shouldExpandTotalTonnage = totalTonnageDigits >= 8

  const clearFilters = () => {
    setHasUserInteracted(true)
    setFilters({
      dateFrom: "",
      dateTo: "",
      origins: new Set(),
      destinations: new Set(),
      vehicleTypes: new Set(),
      shipmentIds: new Set(),
      vehicleIds: new Set(),
    })
  }

  // Track user interactions with filters
  const handleFilterChange = (filterType: string, values: any) => {
    setHasUserInteracted(true)
    setFilters((prev) => ({ ...prev, [filterType]: values }))
  }

  const handleDateChange = (from: string, to: string) => {
    setHasUserInteracted(true)
    setFilters((prev) => ({ ...prev, dateFrom: from, dateTo: to }))
  }

  // Only count user-visible filters for the active count
  const activeFiltersCount =
    filters.origins.size +
    filters.destinations.size +
    filters.vehicleTypes.size +
    filters.shipmentIds.size +
    filters.vehicleIds.size +
    (hasUserInteracted && filters.dateFrom ? 1 : 0) +
    (hasUserInteracted && filters.dateTo ? 1 : 0)

  // Get date range from data
  const dateRange = useMemo(() => {
    const dates = data
      .map((item) => item.Date?.split("T")[0])
      .filter(Boolean)
      .sort()
    return {
      min: dates[0] || "",
      max: dates[dates.length - 1] || "",
    }
  }, [data])

  const originOptions = uniqueOrigins.map((origin) => ({
    label: origin,
    value: origin,
  }))

  const destinationOptions = uniqueDestinations.map((destination) => ({
    label: destination,
    value: destination,
  }))

  const vehicleTypeOptions = uniqueVehicleTypes.map((type) => ({
    label: type,
    value: type,
  }))

  const shipmentIdOptions = uniqueShipmentIds.map((id) => ({
    label: id,
    value: id,
  }))

  const vehicleIdOptions = uniqueVehicleIds.map((id) => ({
    label: id,
    value: id,
  }))

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <div className="space-y-2">
            <p className="text-lg font-medium text-foreground">Loading Dashboard</p>
            <p className="text-sm text-muted-foreground">Preparing your tonnage analytics...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto p-6 space-y-8">
        {/* Enhanced Header */}
        <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
                <Truck className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-foreground">Cargo Tonnage Analytics</h1>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setExportModalOpen(true)}
              className="bg-transparent border-green-600 text-green-400 hover:bg-green-600 hover:text-white"
            >
              <Download className="h-4 w-4 mr-2" />
              Export Data
            </Button>
            <Link href="/metrics">
              <Button
                size="sm"
                variant="outline"
                className="bg-transparent border-blue-600 text-blue-400 hover:bg-blue-600 hover:text-white"
              >
                <BarChart3 className="h-4 w-4 mr-2" />
                Metrics
              </Button>
            </Link>
            <Link href="/data-management">
              <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground">
                <Plus className="h-4 w-4 mr-2" />
                Add Tonnage Data
              </Button>
            </Link>
          </div>
        </div>

        {/* Enhanced Filters Card */}
        <Card className="bg-card border-border shadow-xl">
          <CardContent className="p-6 flex items-center min-h-[80px]">
            <div className="flex flex-wrap gap-3 items-center justify-between w-full">
              <div className="flex flex-wrap gap-3">
                {/* Date Range Filter - Only show badge if user has interacted */}
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className={cn(
                        "h-9 border-dashed bg-background hover:bg-accent text-foreground border-border transition-colors",
                        hasUserInteracted &&
                          (filters.dateFrom || filters.dateTo) &&
                          "border-primary/50 bg-primary/10 text-primary",
                      )}
                    >
                      <Calendar className="mr-2 h-4 w-4" />
                      Date Range
                      {hasUserInteracted && (filters.dateFrom || filters.dateTo) && (
                        <>
                          <Separator orientation="vertical" className="mx-2 h-4 bg-border" />
                          <Badge
                            variant="secondary"
                            className="rounded-sm px-1.5 font-normal bg-primary/20 text-primary border-primary/50"
                          >
                            {filters.dateFrom && filters.dateTo
                              ? `${new Date(filters.dateFrom).toLocaleDateString("en-US", { month: "short", day: "numeric" })} - ${new Date(filters.dateTo).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`
                              : "Custom"}
                          </Badge>
                        </>
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0 bg-popover border-border shadow-xl z-40" align="start">
                    <DateRangePicker
                      dateFrom={hasUserInteracted ? filters.dateFrom : ""}
                      dateTo={hasUserInteracted ? filters.dateTo : ""}
                      onDateChange={handleDateChange}
                      minDate={dateRange.min}
                      maxDate={dateRange.max}
                    />
                  </PopoverContent>
                </Popover>

                <FacetedFilter
                  title="Origin"
                  options={originOptions}
                  selectedValues={filters.origins}
                  onSelectionChange={(values) => handleFilterChange("origins", values)}
                />
                <FacetedFilter
                  title="Destination"
                  options={destinationOptions}
                  selectedValues={filters.destinations}
                  onSelectionChange={(values) => handleFilterChange("destinations", values)}
                />
                <FacetedFilter
                  title="Vehicle Type"
                  options={vehicleTypeOptions}
                  selectedValues={filters.vehicleTypes}
                  onSelectionChange={(values) => handleFilterChange("vehicleTypes", values)}
                />
                <FacetedFilter
                  title="Shipment ID"
                  options={shipmentIdOptions}
                  selectedValues={filters.shipmentIds}
                  onSelectionChange={(values) => handleFilterChange("shipmentIds", values)}
                />
                <FacetedFilter
                  title="Vehicle ID"
                  options={vehicleIdOptions}
                  selectedValues={filters.vehicleIds}
                  onSelectionChange={(values) => handleFilterChange("vehicleIds", values)}
                />
              </div>

              {/* Clear All Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={clearFilters}
                disabled={activeFiltersCount === 0}
                className={cn(
                  "h-9 transition-colors",
                  activeFiltersCount > 0
                    ? "text-destructive hover:text-destructive/90 hover:bg-destructive/10 border-destructive/50 hover:border-destructive/40 bg-transparent"
                    : "text-muted-foreground border-border bg-muted/20 cursor-not-allowed",
                )}
              >
                Clear All
                {activeFiltersCount > 0 && (
                  <Badge variant="secondary" className="ml-2 bg-destructive/20 text-destructive border-destructive/50">
                    {activeFiltersCount}
                  </Badge>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Enhanced KPI Cards with Specific Percentage Widths */}
        <div className="flex gap-6 min-w-0">
          {/* Total Tonnage Card - 34% when 8+ digits, 25% otherwise */}
          <Card
            className="bg-card border-border shadow-xl hover:bg-accent/5 transition-colors min-w-0"
            style={{
              width: shouldExpandTotalTonnage ? "34%" : "25%",
            }}
          >
            <CardContent className="p-6 flex flex-col justify-center min-h-[120px]">
              <div className="flex items-center space-x-4">
                <div className="p-1.5 bg-primary/10 rounded-md border border-primary/20">
                  <TrendingUp className="h-4 w-4 text-primary" />
                </div>
                <div className="text-2xl font-bold text-foreground whitespace-nowrap">
                  {totalTonnage.toLocaleString()} kg
                </div>
              </div>
              <CardTitle className="text-sm font-medium text-muted-foreground mt-3">Total Tonnage</CardTitle>
            </CardContent>
          </Card>

          <Card
            className="bg-card border-border shadow-xl hover:bg-accent/5 transition-colors min-w-0"
            style={{
              width: shouldExpandTotalTonnage ? "22%" : "25%",
            }}
          >
            <CardContent className="p-6 flex flex-col justify-center min-h-[120px]">
              <div className="flex items-center space-x-4">
                <div className="p-1.5 bg-emerald-900/30 rounded-md border border-emerald-700/50">
                  <Truck className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-foreground whitespace-nowrap">
                  {totalShipments.toLocaleString()}
                </div>
              </div>
              <CardTitle className="text-sm font-medium text-muted-foreground mt-3">Total Shipments</CardTitle>
            </CardContent>
          </Card>

          <Card
            className="bg-card border-border shadow-xl hover:bg-accent/5 transition-colors min-w-0"
            style={{
              width: shouldExpandTotalTonnage ? "22%" : "25%",
            }}
          >
            <CardContent className="p-6 flex flex-col justify-center min-h-[120px]">
              <div className="flex items-center space-x-4">
                <div className="p-1.5 bg-amber-900/30 rounded-md border border-amber-700/50">
                  <BarChart3 className="h-4 w-4 text-amber-400" />
                </div>
                <div className="text-2xl font-bold text-foreground whitespace-nowrap">
                  {totalShipments > 0 ? (totalTonnage / totalShipments).toFixed(0) : 0} kg
                </div>
              </div>
              <CardTitle className="text-sm font-medium text-muted-foreground mt-3">Avg per Shipment</CardTitle>
            </CardContent>
          </Card>

          {/* Active Routes Card - 22% when Total Tonnage expands, 25% otherwise */}
          <Card
            className="bg-card border-border shadow-xl hover:bg-accent/5 transition-colors min-w-0"
            style={{
              width: shouldExpandTotalTonnage ? "22%" : "25%",
            }}
          >
            <CardContent className="p-6 flex flex-col justify-center min-h-[120px]">
              <div className="flex items-center space-x-4">
                <div className="p-1.5 bg-purple-900/30 rounded-md border border-purple-700/50">
                  <Filter className="h-4 w-4 text-purple-400" />
                </div>
                <div className="text-2xl font-bold text-foreground whitespace-nowrap">
                  {[...new Set(filteredData.map((item) => `${item.Dep}-${item.Arr}`))].filter(Boolean).length}
                </div>
              </div>
              <CardTitle className="text-sm font-medium text-muted-foreground mt-3">Active Routes</CardTitle>
            </CardContent>
          </Card>
        </div>

        {/* Main Trend Chart - Full Width */}
        <InboundOutboundTrendChart
          data={filteredData}
          dateRange={{
            from: filters.dateFrom || dateRange.min,
            to: filters.dateTo || dateRange.max,
            isYTD: !hasUserInteracted && filters.dateFrom === getYearToDateRange().yearStart,
            recordCount: filteredData.length,
          }}
        />

        {/* Secondary Charts - Two Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RouteDistributionChart data={filteredData} />
          <ShipmentTonnageStackedChart data={filteredData} />
        </div>
      </div>

      {/* Export Modal */}
      <ExportModal
        isOpen={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        data={filteredData}
        filteredCount={filteredData.length}
        totalCount={data.length}
      />
    </div>
  )
}
