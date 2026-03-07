"use client"

import dynamic from "next/dynamic"

const GridParticleBackground = dynamic(
  () =>
    import("@/components/grid-particle-background").then(
      (mod) => mod.GridParticleBackground
    ),
  { ssr: false }
)

export function BackgroundWrapper() {
  return <GridParticleBackground />
}
