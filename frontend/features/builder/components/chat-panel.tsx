"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import {
  PromptInput,
  PromptInputHeader,
  PromptInputAttachments,
  PromptInputAttachment,
  PromptInputBody,
  PromptInputTextarea,
  PromptInputFooter,
  PromptInputSubmit,
} from "@/components/ai-elements/prompt-input"

type Message = {
  id: string
  role: "user" | "assistant"
  content: string
}

type ScenarioData = {
  context: string
  persona: {
    name: string
    role: string
    traits: string
  }
  objections: string[]
}

type ChatPanelProps = {
  onScenarioGenerated: (data: ScenarioData) => void
}

export function ChatPanel({ onScenarioGenerated }: ChatPanelProps) {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([])

  const handleSubmit = async (_message: any, event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!input.trim()) return

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
    }
    setMessages((prev) => [...prev, userMessage])

    // Clear input
    setInput("")

    try {
      // Call the API
      const response = await fetch('/api/builder-chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: input,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const data = await response.json()

      console.log('API Response:', data)

      // Pass the structured data to the parent component
      onScenarioGenerated(data)

      // Format the structured response for display in chat
      const formattedResponse = `**Context:**
${data.context}

**Persona:**
- Name: ${data.persona.name}
- Role: ${data.persona.role}
- Traits: ${data.persona.traits}

**Objections:**
${data.objections.map((obj: string, i: number) => `${i + 1}. ${obj}`).join('\n')}`

      // Add AI response to chat
      const aiMessage: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: formattedResponse,
      }
      setMessages((prev) => [...prev, aiMessage])
    } catch (error) {
      console.error('Error getting AI response:', error)
      // Add error message
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
      }
      setMessages((prev) => [...prev, errorMessage])
    }
  }

  return (
    <>
        <div className="relative flex size-full flex-col overflow-hidden">

      {/* Messages area - scrollable, takes up remaining space */}
      <Card className="flex-1 rounded-none border-0 overflow-auto">
        <CardContent className="p-4 space-y-4">
          {messages.length === 0 ? (
            <p className="text-sm text-muted-foreground">Start a conversation...</p>
          ) : (
            messages.map((msg) => (
              <Card
                key={msg.id}
                className={msg.role === "user"
                  ? "ml-auto w-fit max-w-[80%]"
                  : "mr-auto w-fit max-w-[80%]"
                }
              >
                <CardContent className="p-3">
                  <p className="text-sm break-words">{msg.content}</p>
                </CardContent>
              </Card>
            ))
          )}
        </CardContent>
      </Card>

      {/* Chat input at bottom - fixed */}
      <Card className="flex-none rounded-none border-0 ">
        <CardContent className="p-4">
          <PromptInput globalDrop multiple onSubmit={handleSubmit}>
            {/* <PromptInputHeader>
              <PromptInputAttachments>
                {(attachment) => <PromptInputAttachment data={attachment} />}
              </PromptInputAttachments>
            </PromptInputHeader> */}
            <PromptInputBody>
              <PromptInputTextarea
                onChange={(e) => setInput(e.target.value)}
                value={input}
              />
            </PromptInputBody>
            <PromptInputFooter>
              <PromptInputSubmit disabled={!input} />
            </PromptInputFooter>
          </PromptInput>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
