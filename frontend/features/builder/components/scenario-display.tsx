"use client"

import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

type ScenarioData = {
  context: string
  persona: {
    name: string
    role: string
    traits: string
  }
  objections: string[]
}

type ScenarioDisplayProps = {
  data?: ScenarioData
}

export function ScenarioDisplay({ data }: ScenarioDisplayProps) {
  if (!data) {
    return (
      <Card className="flex-1 rounded-none border-0">
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground text-center">
            Start a conversation to generate a scenario...
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      {/* Context Card */}
      <Card className="flex-none rounded-none border-0">
        <CardHeader>
          <CardTitle>Context</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">{data.context}</p>
        </CardContent>
      </Card>

      {/* Persona Card */}
      <Card className="flex-none rounded-none border-0 border-t">
        <CardHeader>
          <CardTitle>Persona</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div>
            <p className="text-sm font-medium">{data.persona.name}</p>
            <p className="text-sm text-muted-foreground">{data.persona.role}</p>
          </div>
          <p className="text-sm">
            <span className="font-medium">Traits: </span>
            {data.persona.traits}
          </p>
        </CardContent>
      </Card>

      {/* Objections Card */}
      <Card className="flex-1 rounded-none border-0 border-t overflow-auto">
        <CardHeader>
          <CardTitle>Objections</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {data.objections.map((objection, index) => (
              <li key={index} className="text-sm">
                {objection}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </>
  )
}
