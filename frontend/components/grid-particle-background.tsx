"use client"

import { useEffect, useRef } from "react"

export function GridParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let animationId: number
    let time = 0
    const mouse = { x: canvas.width / 2, y: canvas.height / 2 }

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener("resize", resize)

    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX
      mouse.y = e.clientY
    }
    window.addEventListener("mousemove", handleMouseMove)

    // Glow light configs (simulates the Three.js point lights)
    const glowLights = [
      { bx: 0.25, by: 0.3, radius: 350, r: 14, g: 165, b: 233, a: 0.07, phaseX: 0, phaseY: 0.5 },
      { bx: 0.75, by: 0.7, radius: 300, r: 99, g: 102, b: 241, a: 0.06, phaseX: 1.5, phaseY: 0 },
      { bx: 0.5, by: 0.5, radius: 250, r: 56, g: 189, b: 248, a: 0.04, phaseX: 3, phaseY: 2 },
    ]

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const speed = 0.0008

      // Draw ambient glow lights
      glowLights.forEach((light) => {
        const cx = (light.bx + Math.sin(time * speed * 1.2 + light.phaseX) * 0.08) * canvas.width
        const cy = (light.by + Math.cos(time * speed + light.phaseY) * 0.08) * canvas.height
        const r = light.radius * (Math.min(canvas.width, canvas.height) / 900)

        const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, r)
        gradient.addColorStop(0, `rgba(${light.r}, ${light.g}, ${light.b}, ${light.a})`)
        gradient.addColorStop(0.5, `rgba(${light.r}, ${light.g}, ${light.b}, ${light.a * 0.4})`)
        gradient.addColorStop(1, "transparent")
        ctx.fillStyle = gradient
        ctx.fillRect(0, 0, canvas.width, canvas.height)
      })

      // Mouse-following glow (simulates interactive mouse light)
      const mouseGlow = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 280)
      mouseGlow.addColorStop(0, "rgba(255, 255, 255, 0.03)")
      mouseGlow.addColorStop(0.4, "rgba(14, 165, 233, 0.02)")
      mouseGlow.addColorStop(1, "transparent")
      ctx.fillStyle = mouseGlow
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      time++
      animationId = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      window.removeEventListener("resize", resize)
      window.removeEventListener("mousemove", handleMouseMove)
      cancelAnimationFrame(animationId)
    }
  }, [])

  return (
    <div className="fixed inset-0 -z-10">
      {/* Canvas glow layer */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full"
        aria-hidden="true"
      />

      {/* CSS Grid overlay */}
      <div className="absolute inset-0 overflow-hidden opacity-[0.04] pointer-events-none z-10">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(rgba(14, 165, 233, 1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(14, 165, 233, 1) 1px, transparent 1px)
            `,
            backgroundSize: "60px 60px",
          }}
        />
      </div>

      {/* Noise texture overlay */}
      <div
        className="absolute inset-0 opacity-[0.06] pointer-events-none z-20 mix-blend-overlay"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />
    </div>
  )
}
