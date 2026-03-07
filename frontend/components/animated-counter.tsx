"use client"

import { useEffect, useRef, useState } from "react"
import { motion, useInView, useSpring, useTransform } from "framer-motion"

interface AnimatedCounterProps {
  value: number | string
  className?: string
  duration?: number
}

export function AnimatedCounter({ value, className, duration = 1.2 }: AnimatedCounterProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true })

  // Handle string values like "72%"
  const numericValue = typeof value === "string" ? parseFloat(value) : value
  const suffix = typeof value === "string" ? value.replace(/[\d.]/g, "") : ""
  const isValidNumber = !isNaN(numericValue)

  const spring = useSpring(0, { duration: duration * 1000, bounce: 0 })
  const display = useTransform(spring, (v) =>
    isValidNumber ? `${Math.round(v)}${suffix}` : String(value)
  )

  useEffect(() => {
    if (isInView && isValidNumber) {
      spring.set(numericValue)
    }
  }, [isInView, numericValue, spring, isValidNumber])

  if (!isValidNumber) {
    return <span className={className}>{value}</span>
  }

  return <motion.span ref={ref} className={className}>{display}</motion.span>
}
