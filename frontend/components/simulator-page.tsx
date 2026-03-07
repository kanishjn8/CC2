"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Zap,
  Warehouse,
  Truck,
  TrafficCone,
  AlertTriangle,
  CheckCircle,
  Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"
import type { SimulationResponse } from "@/lib/types"

// Mock trigger — returns a fake success response after a short delay
function mockTrigger(title: string): () => Promise<SimulationResponse> {
  return () =>
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            status: "ok",
            message: `${title} scenario triggered successfully (mock).`,
            events_generated: Math.floor(Math.random() * 8) + 3,
          }),
        800
      )
    )
}

interface ScenarioConfig {
  id: string
  title: string
  description: string
  impact: string
  icon: LucideIcon
  color: string
  borderColor: string
  bgColor: string
  trigger: () => Promise<SimulationResponse>
}

export default function SimulatorPage() {
  const [results, setResults] = useState<Record<string, SimulationResponse | null>>({})
  const [loadingId, setLoadingId] = useState<string | null>(null)

  const scenarios: ScenarioConfig[] = [
    {
      id: "warehouse",
      title: "Warehouse Congestion",
      description:
        "Simulates a sudden surge in warehouse load, causing congestion at a major hub. The AI agent should detect the bottleneck and recommend reprioritizing or rerouting affected shipments.",
      impact: "Increases warehouse load to 95%+, queues spike, congestion score critical",
      icon: Warehouse,
      color: "text-amber-400",
      borderColor: "border-amber-500/30",
      bgColor: "bg-amber-500/10",
      trigger: mockTrigger("Warehouse Congestion"),
    },
    {
      id: "carrier",
      title: "Carrier Failure",
      description:
        "Simulates a carrier experiencing systemic failures — high delay probability, low pickup success rate. The AI agent should flag carrier degradation and recommend switching carriers for affected shipments.",
      impact: "Carrier reliability drops below 0.3, delay probability > 70%",
      icon: Truck,
      color: "text-red-400",
      borderColor: "border-red-500/30",
      bgColor: "bg-red-500/10",
      trigger: mockTrigger("Carrier Failure"),
    },
    {
      id: "traffic",
      title: "Traffic Spike",
      description:
        "Simulates a major traffic disruption on key routes, causing ETA drift for multiple shipments. The AI agent should detect emerging delay risks and suggest rerouting or escalation.",
      impact: "Traffic level → CRITICAL on major corridors, ETAs shift 2-4 hours",
      icon: TrafficCone,
      color: "text-purple-400",
      borderColor: "border-purple-500/30",
      bgColor: "bg-purple-500/10",
      trigger: mockTrigger("Traffic Spike"),
    },
  ]

  const handleTrigger = async (scenario: ScenarioConfig) => {
    setLoadingId(scenario.id)
    setResults((prev) => ({ ...prev, [scenario.id]: null }))

    try {
      const result = await scenario.trigger()
      setResults((prev) => ({ ...prev, [scenario.id]: result }))
    } catch {
      setResults((prev) => ({
        ...prev,
        [scenario.id]: {
          status: "error",
          message: `Failed to trigger ${scenario.title}. Is the backend running?`,
          events_generated: 0,
        },
      }))
    } finally {
      setLoadingId(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-primary/10 border border-primary/20">
              <Zap className="h-6 w-6 text-primary" />
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-foreground">Disruption Scenario Simulator</h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Trigger simulated disruptions to demonstrate how the AI agent detects, reasons about,
                and responds to operational risks in real time. Each scenario modifies the simulation
                state and triggers the agent&apos;s observe → reason → decide → act loop.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Scenario Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {scenarios.map((scenario) => {
          const Icon = scenario.icon
          const result = results[scenario.id]
          const isLoading = loadingId === scenario.id

          return (
            <Card key={scenario.id} className={cn("border transition-all", scenario.borderColor)}>
              <CardHeader>
                <div className="flex items-center gap-3 mb-2">
                  <div className={cn("p-2.5 rounded-lg border", scenario.bgColor, scenario.borderColor)}>
                    <Icon className={cn("h-5 w-5", scenario.color)} />
                  </div>
                  <CardTitle className="text-base font-semibold text-foreground">
                    {scenario.title}
                  </CardTitle>
                </div>
                <CardDescription className="text-xs leading-relaxed">
                  {scenario.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Impact */}
                <div className="rounded-lg bg-accent p-3">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Expected Impact
                  </p>
                  <p className="text-xs text-foreground">{scenario.impact}</p>
                </div>

                {/* Trigger Button */}
                <Button
                  className="w-full"
                  variant={scenario.id === "carrier" ? "destructive" : "default"}
                  disabled={isLoading}
                  onClick={() => handleTrigger(scenario)}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Triggering...
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4 mr-2" />
                      Simulate {scenario.title}
                    </>
                  )}
                </Button>

                {/* Result */}
                {result && (
                  <div
                    className={cn(
                      "rounded-lg border p-3 text-xs",
                      result.status !== "error"
                        ? "border-emerald-500/30 bg-emerald-500/10"
                        : "border-red-500/30 bg-red-500/10"
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {result.status !== "error" ? (
                        <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                      ) : (
                        <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
                      )}
                      <span className={cn("font-semibold", result.status !== "error" ? "text-emerald-400" : "text-red-400")}>
                        {result.status !== "error" ? "Scenario Triggered" : "Failed"}
                      </span>
                    </div>
                    <p className="text-muted-foreground">{result.message}</p>
                    {result.events_generated > 0 && (
                      <p className="mt-1 text-muted-foreground">
                        Events generated: <span className="text-foreground font-semibold">{result.events_generated}</span>
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* How it works */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-muted-foreground">
            How Scenario Simulation Works
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {[
              { step: "1", label: "Trigger", desc: "Operator triggers a disruption scenario" },
              { step: "2", label: "Observe", desc: "AI agent detects changed operational signals" },
              { step: "3", label: "Reason", desc: "Agent analyzes root cause and affected shipments" },
              { step: "4", label: "Decide", desc: "Agent evaluates and scores possible interventions" },
              { step: "5", label: "Act", desc: "Agent executes or recommends corrective actions" },
            ].map((item) => (
              <div key={item.step} className="text-center space-y-2">
                <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 border border-primary/20 text-primary font-bold text-sm">
                  {item.step}
                </div>
                <p className="text-xs font-semibold text-foreground">{item.label}</p>
                <p className="text-[10px] text-muted-foreground leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
