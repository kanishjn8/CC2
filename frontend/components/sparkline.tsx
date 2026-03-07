"use client"

import { cn } from "@/lib/utils"

interface SparklineProps {
  data: number[]
  color?: string
  className?: string
  height?: number
  width?: number
}

export function Sparkline({
  data,
  color = "hsl(199, 89%, 48%)",
  className,
  height = 24,
  width = 64,
}: SparklineProps) {
  if (data.length < 2) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - ((v - min) / range) * (height - 2) - 1
    return `${x},${y}`
  })

  const pathD = `M${points.join(" L")}`
  // Fill area
  const fillD = `${pathD} L${width},${height} L0,${height} Z`

  return (
    <svg
      className={cn("overflow-visible", className)}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
    >
      <defs>
        <linearGradient id={`spark-fill-${color.replace(/[^a-z0-9]/gi, "")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path
        d={fillD}
        fill={`url(#spark-fill-${color.replace(/[^a-z0-9]/gi, "")})`}
      />
      <path
        d={pathD}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
