"use client"

import type * as React from "react"
import { useState } from "react"
import { Check, PlusCircle, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"

interface FacetedFilterProps {
  title?: string
  options: {
    label: string
    value: string
    icon?: React.ComponentType<{ className?: string }>
  }[]
  selectedValues: Set<string>
  onSelectionChange: (values: Set<string>) => void
}

export function FacetedFilter({ title, options, selectedValues, onSelectionChange }: FacetedFilterProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [isOpen, setIsOpen] = useState(false)

  const filteredOptions = options.filter((option) => option.label.toLowerCase().includes(searchTerm.toLowerCase()))

  const handleToggleOption = (optionValue: string) => {
    const newValues = new Set(selectedValues)
    if (selectedValues.has(optionValue)) {
      newValues.delete(optionValue)
    } else {
      newValues.add(optionValue)
    }
    onSelectionChange(newValues)
  }

  const handleClearAll = () => {
    onSelectionChange(new Set())
    setIsOpen(false)
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(
            "h-9 border-dashed bg-background hover:bg-accent text-foreground border-border transition-colors",
            selectedValues.size > 0 && "border-primary/50 bg-primary/10 text-primary",
          )}
        >
          <PlusCircle className="mr-2 h-4 w-4" />
          {title}
          {selectedValues.size > 0 && (
            <>
              <Separator orientation="vertical" className="mx-2 h-4 bg-border" />
              <Badge
                variant="secondary"
                className="rounded-sm px-1.5 font-normal bg-primary/20 text-primary border-primary/50"
              >
                {selectedValues.size}
              </Badge>
              <div className="hidden space-x-1 lg:flex">
                {selectedValues.size > 2 ? (
                  <Badge
                    variant="secondary"
                    className="rounded-sm px-1.5 font-normal bg-primary/20 text-primary border-primary/50"
                  >
                    {selectedValues.size} selected
                  </Badge>
                ) : (
                  options
                    .filter((option) => selectedValues.has(option.value))
                    .map((option) => (
                      <Badge
                        variant="secondary"
                        key={option.value}
                        className="rounded-sm px-1.5 font-normal bg-primary/20 text-primary border-primary/50"
                      >
                        {option.label}
                      </Badge>
                    ))
                )}
              </div>
            </>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0 bg-popover border-border z-40" align="start">
        <div className="p-2 space-y-2">
          {/* Search Input */}
          <Input
            placeholder={`Search ${title?.toLowerCase()}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="h-8 text-sm"
          />

          {/* Options List */}
          <div className="max-h-[200px] overflow-y-auto space-y-1">
            {filteredOptions.length === 0 ? (
              <div className="py-2 text-center text-sm text-muted-foreground">No results found</div>
            ) : (
              filteredOptions.map((option) => {
                const isSelected = selectedValues.has(option.value)
                return (
                  <div
                    key={option.value}
                    className="flex items-center space-x-2 p-2 rounded-sm hover:bg-accent cursor-pointer transition-colors"
                    onClick={() => handleToggleOption(option.value)}
                  >
                    <div
                      className={cn(
                        "flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                        isSelected ? "bg-primary text-primary-foreground" : "opacity-50",
                      )}
                    >
                      {isSelected && <Check className="h-3 w-3" />}
                    </div>
                    {option.icon && <option.icon className="h-4 w-4 text-muted-foreground" />}
                    <span className="text-sm text-foreground flex-1">{option.label}</span>
                  </div>
                )
              })
            )}
          </div>

          {/* Clear All Button */}
          {selectedValues.size > 0 && (
            <>
              <Separator />
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearAll}
                className="w-full justify-center text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4 mr-1" />
                Clear filters
              </Button>
            </>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
