"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import {
  LayoutDashboard,
  Package,
  Warehouse,
  Truck,
  Brain,
  Zap,
  Search,
  ArrowRight,
} from "lucide-react"
import { useShipments } from "@/hooks/use-data"

const PAGES = [
  { href: "/", label: "Overview Dashboard", icon: LayoutDashboard },
  { href: "/shipments", label: "Shipments Explorer", icon: Package },
  { href: "/warehouses", label: "Warehouse Monitor", icon: Warehouse },
  { href: "/carriers", label: "Carrier Performance", icon: Truck },
  { href: "/decisions", label: "AI Decisions Log", icon: Brain },
  { href: "/simulator", label: "Disruption Simulator", icon: Zap },
]

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const { data: shipments } = useShipments()

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setOpen((v) => !v)
      }
    }
    document.addEventListener("keydown", onKeyDown)
    return () => document.removeEventListener("keydown", onKeyDown)
  }, [])

  const navigate = useCallback(
    (href: string) => {
      setOpen(false)
      router.push(href)
    },
    [router]
  )

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search pages, shipments, actions..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Pages">
          {PAGES.map((page) => {
            const Icon = page.icon
            return (
              <CommandItem
                key={page.href}
                onSelect={() => navigate(page.href)}
                className="gap-2"
              >
                <Icon className="h-4 w-4 text-muted-foreground" />
                {page.label}
              </CommandItem>
            )
          })}
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Shipments">
          {shipments.slice(0, 8).map((s) => (
            <CommandItem
              key={s.shipment_id}
              onSelect={() => navigate("/shipments")}
              className="gap-2"
            >
              <Package className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-xs">{s.shipment_id}</span>
              <span className="text-muted-foreground text-xs">
                {s.origin} → {s.destination}
              </span>
              {s.delay_risk >= 0.7 && (
                <span className="ml-auto text-[10px] text-red-400 font-semibold">
                  Risk {Math.round(s.delay_risk * 100)}%
                </span>
              )}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Quick Actions">
          <CommandItem onSelect={() => navigate("/simulator")} className="gap-2">
            <Zap className="h-4 w-4 text-amber-400" />
            Simulate Warehouse Congestion
          </CommandItem>
          <CommandItem onSelect={() => navigate("/simulator")} className="gap-2">
            <Zap className="h-4 w-4 text-red-400" />
            Simulate Carrier Failure
          </CommandItem>
          <CommandItem onSelect={() => navigate("/simulator")} className="gap-2">
            <Zap className="h-4 w-4 text-purple-400" />
            Simulate Traffic Spike
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
