import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ---- Logistics Utility Helpers ----

export function getRiskColor(risk: number): string {
  if (risk >= 0.7) return "text-red-400"
  if (risk >= 0.4) return "text-amber-400"
  return "text-emerald-400"
}

export function getRiskBg(risk: number): string {
  if (risk >= 0.7) return "bg-red-500/10 border-red-500/20"
  if (risk >= 0.4) return "bg-amber-500/10 border-amber-500/20"
  return "bg-emerald-500/10 border-emerald-500/20"
}

export function getRiskLabel(risk: number): string {
  if (risk >= 0.7) return "Critical"
  if (risk >= 0.4) return "Warning"
  return "Normal"
}

export function getCongestionColor(score: number): string {
  if (score >= 0.8) return "text-red-400"
  if (score >= 0.5) return "text-amber-400"
  return "text-emerald-400"
}

export function getHealthColor(score: number): string {
  if (score >= 80) return "text-emerald-400"
  if (score >= 60) return "text-amber-400"
  return "text-red-400"
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

export function formatTimestamp(ts: string): string {
  return new Date(ts).toLocaleString("en-IN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function formatTimeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "Just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}
