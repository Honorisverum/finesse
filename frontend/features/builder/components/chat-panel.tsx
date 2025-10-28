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

export function ChatPanel() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([])

  const handleSubmit = (message: any, event: React.FormEvent<HTMLFormElement>) => {
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

    // Mock AI response after a short delay
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
      }
      setMessages((prev) => [...prev, aiMessage])
    }, 500)
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
