"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { ArrowUp, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

type Message = {
  id: string
  text: string
  sender: "user" | "bot"
  timestamp: Date
}

type ConversationStep = "initial" | "aspects" | "pitfalls" | "generating"

const suggestionPills = ["Active listening", "Giving feedback", "Conflict resolution", "Empathy", "Negotiation", "More"]

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [step, setStep] = useState<ConversationStep>("initial")
  const [isShifted, setIsShifted] = useState(false)
  const [userSkill, setUserSkill] = useState("")
  const [showInitial, setShowInitial] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const addBotMessage = (text: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: "bot",
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, newMessage])
  }

  const addUserMessage = (text: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: "user",
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, newMessage])
  }

  const handleSend = (text?: string) => {
    const messageText = text || input
    if (!messageText.trim()) return

    if (showInitial) {
      setShowInitial(false)
    }

    addUserMessage(messageText)
    const userInput = messageText
    setInput("")

    // Handle conversation flow
    setTimeout(() => {
      if (step === "initial") {
        setUserSkill(userInput)
        addBotMessage(`Which aspects of ${userInput} are important to you?`)
        setStep("aspects")
      } else if (step === "aspects") {
        addBotMessage(`What potential pitfalls in ${userInput} could there be?`)
        setStep("pitfalls")
      } else if (step === "pitfalls") {
        setStep("generating")
        setTimeout(() => {
          setIsShifted(true)
        }, 300)
      }
    }, 600)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      <header className="fixed left-0 right-0 top-0 z-50 flex items-center justify-center border-b border-border/50 bg-background/80 px-4 py-4 backdrop-blur-sm">
        <h1 className="text-balance text-center text-lg text-foreground">
          <span className="text-2xl font-bold text-orange-500">Kiyomi App</span>
          <br />
          <span className="font-normal">Learning Any People Skills Stress-Free via AI Gaming</span>
        </h1>
      </header>

      <div className="flex flex-1 items-center justify-center pt-16">
        {showInitial && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-8 pt-16 animate-in fade-in duration-500">
            <h1 className="text-balance text-center text-4xl font-medium text-foreground">What can I help with?</h1>

            <div className="w-full max-w-3xl px-4">
              {/* Input box */}
              <div className="relative mb-6">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Which people skill do you want to improve?"
                  className="w-full rounded-3xl border-0 bg-card px-6 py-5 pr-14 text-lg text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/20"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim()}
                  className={cn(
                    "absolute right-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full transition-colors",
                    input.trim()
                      ? "bg-foreground text-background hover:bg-foreground/90"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  <ArrowUp className="h-5 w-5" />
                </button>
              </div>

              {/* Suggestion pills */}
              <div className="flex flex-wrap items-center justify-center gap-2">
                {suggestionPills.map((pill) => (
                  <button
                    key={pill}
                    onClick={() => handleSend(pill)}
                    className="rounded-full border border-border bg-transparent px-4 py-2.5 text-sm text-secondary-foreground transition-colors hover:bg-card"
                  >
                    {pill}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {!showInitial && (
          <div
            className={cn(
              "flex h-full w-full max-w-3xl flex-col transition-all duration-700 ease-in-out",
              isShifted && "fixed bottom-8 left-8 h-[500px] w-[400px] max-w-none scale-90",
            )}
          >
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-8">
              <div className={cn("space-y-6", !isShifted && "mx-auto max-w-3xl")}>
                {messages.map((message, index) => (
                  <div
                    key={message.id}
                    className={cn(
                      "flex animate-in fade-in slide-in-from-bottom-2 duration-500",
                      message.sender === "user" ? "justify-end" : "justify-start",
                    )}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    {message.sender === "bot" && (
                      <div className="mr-3 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-card">
                        <Sparkles className="h-4 w-4 text-foreground" />
                      </div>
                    )}
                    <div
                      className={cn(
                        "max-w-[80%] rounded-2xl px-5 py-3 text-pretty",
                        message.sender === "user" ? "bg-card text-card-foreground" : "bg-transparent text-foreground",
                      )}
                    >
                      <p className="text-sm leading-relaxed">{message.text}</p>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>

            <div className="border-t border-border bg-background px-4 py-4">
              <div className={cn(!isShifted && "mx-auto max-w-3xl")}>
                <div className="relative">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder={
                      step === "generating" ? "What don't you like about the scenario?" : "Type your response..."
                    }
                    className="w-full rounded-3xl border-0 bg-card px-6 py-4 pr-14 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/20"
                  />
                  <button
                    onClick={() => handleSend()}
                    disabled={!input.trim()}
                    className={cn(
                      "absolute right-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full transition-colors",
                      input.trim()
                        ? "bg-foreground text-background hover:bg-foreground/90"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    <ArrowUp className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {isShifted && (
          <div className="absolute right-8 top-1/2 w-[500px] -translate-y-1/2 animate-in fade-in slide-in-from-right duration-700">
            <div className="rounded-2xl border border-border bg-card p-8 shadow-2xl">
              <div className="mb-6 flex flex-col items-center gap-4 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                  <Sparkles className="h-6 w-6 animate-pulse text-foreground" />
                </div>
                <h3 className="text-xl font-semibold text-card-foreground">Generating Scenario</h3>
              </div>
              <div className="space-y-4">
                {/* Loading spinner animation */}
                <div className="flex items-center justify-center py-8">
                  <div className="relative h-16 w-16">
                    <div className="absolute inset-0 rounded-full border-4 border-muted"></div>
                    <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-foreground"></div>
                  </div>
                </div>
                {/* Progress bar */}
                <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full w-2/3 animate-pulse rounded-full bg-foreground transition-all duration-1000"
                    style={{ animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite" }}
                  />
                </div>
                <p className="text-center text-sm text-muted-foreground">
                  Creating a personalized practice scenario based on your responses...
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
