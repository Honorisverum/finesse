"use client"

import { useRouter } from "next/navigation"
import { useEffect } from "react"

export default function HomePage() {
  const router = useRouter()

  useEffect(() => {
    router.push("/builder")
  }, [router])

  return (
    <div className="flex items-center justify-center h-full">
      <p className="text-muted-foreground">Redirecting to builder...</p>
    </div>
  )
}
