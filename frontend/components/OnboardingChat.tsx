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

type ConversationStep = "initial" | "followup" | "generating"

const suggestionPills = ["Dating", "Rizz", "Confidence", "Small Talk", "Leadership", "Persuasion", "Humor", "Conflict Resolution", "Managing Up", "Saying No", "Manipulation Defense"]

interface OnboardingChatProps {
  onComplete: (chatHistory: Array<{role: string, content: string}>) => void
  showMainContent: boolean
}

export default function OnboardingChat({ onComplete, showMainContent }: OnboardingChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [step, setStep] = useState<ConversationStep>("initial")
  const [isShifted, setIsShifted] = useState(false)
  const [userSkill, setUserSkill] = useState("")
  const [showInitial, setShowInitial] = useState(true)
  const [showSuccessMessage, setShowSuccessMessage] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  
  // Автоматически скрываем сообщение "Ready" через 2.5 секунды
  useEffect(() => {
    if (showMainContent) {
      setShowSuccessMessage(true)
      const timer = setTimeout(() => {
        setShowSuccessMessage(false)
      }, 2500)
      return () => clearTimeout(timer)
    }
  }, [showMainContent])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTo({
          top: messagesContainerRef.current.scrollHeight,
          behavior: 'smooth'
        })
      }
    }, 50)
    return () => clearTimeout(timer)
  }, [messages, isShifted])

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

  const handleSend = async (text?: string) => {
    const messageText = text || input
    if (!messageText.trim()) return

    if (showInitial) {
      setShowInitial(false)
    }

    addUserMessage(messageText)
    const userInput = messageText
    setInput("")

    if (step === "initial") {
      // Call LLM to generate smart follow-up question
      setUserSkill(userInput)

      try {
        // Show typing indicator after a brief delay
        setTimeout(async () => {
          const response = await fetch('/api/generate-followup', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              userInput: messageText
            })
          });

          if (response.ok) {
            const data = await response.json();
            addBotMessage(data.question);
          } else {
            // Fallback to generic question if API fails
            addBotMessage(`Tell me more about what you'd like to practice with ${messageText}.`);
          }
          setStep("followup")
        }, 600);
      } catch (error) {
        console.error('Error generating follow-up:', error);
        // Fallback to generic question
        setTimeout(() => {
          addBotMessage(`Tell me more about what you'd like to practice with ${messageText}.`);
          setStep("followup")
        }, 600);
      }
    } else if (step === "followup") {
      // After follow-up answer, start generating scenarios
      setTimeout(() => {
        setIsShifted(true)

        setTimeout(() => {
          setStep("generating")

          setTimeout(() => {
            // Формируем chat_history из всех сообщений
            const chatHistory = messages.map(msg => ({
              role: msg.sender === "user" ? "user" : "assistant",
              content: msg.text
            }));
            onComplete(chatHistory)
          }, 5000)
        }, 800)
      }, 500)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* Header - всегда сверху */}
      <header className="fixed left-0 right-0 top-0 z-50 flex items-center justify-center border-b border-border/50 bg-background/80 px-4 py-4 backdrop-blur-sm">
        <h1 className="text-balance text-center text-lg text-foreground">
          <span className="text-2xl font-bold text-orange-500">Kiyomi App</span>
          <br />
          <span className="font-normal">Learning Any People Skills Stress-Free via AI Gaming</span>
        </h1>
      </header>

      {/* Chat Section */}
      <div 
        className={cn(
          "transition-all duration-700 ease-in-out",
          isShifted 
            ? "fixed bottom-8 left-8 h-[calc(100vh-120px)] w-[450px] z-30" 
            : "fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[768px] max-w-3xl"
        )}
      >
        {showInitial && !isShifted && (
          <div className="flex flex-col items-center justify-center gap-10 animate-in fade-in duration-500">
            <h1 className="text-balance text-center text-[32px] font-semibold text-white tracking-tight">What can I help with?</h1>

            <div className="w-full px-4">
              <div className="relative mb-4">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="What skill do you want to improve?"
                  className="w-full rounded-[26px] border-0 bg-[#2f2f2f] px-5 py-[14px] pr-[52px] text-[15px] text-white placeholder:text-[#8e8e8e] focus:outline-none shadow-sm"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim()}
                  className={cn(
                    "absolute right-2 top-1/2 flex h-[34px] w-[34px] -translate-y-1/2 items-center justify-center rounded-full transition-all",
                    input.trim()
                      ? "bg-white text-black hover:bg-white/90"
                      : "bg-[#676767] text-[#8e8e8e]",
                  )}
                >
                  <ArrowUp className="h-[18px] w-[18px]" strokeWidth={2.5} />
                </button>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-2">
                {suggestionPills.map((pill) => (
                  <button
                    key={pill}
                    onClick={() => handleSend(pill)}
                    className="rounded-full border border-[#4d4d4d] bg-transparent px-3 py-2 text-[13px] text-[#ececec] transition-all hover:bg-[#2f2f2f]"
                  >
                    {pill}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {!showInitial && (
          <div className="flex h-full w-full flex-col bg-[#212121] rounded-xl border border-[#3f3f3f] shadow-2xl overflow-hidden">
            <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-6 scroll-smooth">
              <div className={cn("space-y-5 flex flex-col", isShifted && "space-y-4")}>
                {messages.map((message, index) => (
                  <div
                    key={message.id}
                    className={cn(
                      "flex animate-in fade-in slide-in-from-bottom-1 duration-400",
                      message.sender === "user" ? "justify-end" : "justify-start",
                    )}
                    style={{ animationDelay: `${index * 40}ms` }}
                  >
                    {message.sender === "bot" && (
                      <div className={cn(
                        "mr-2 flex shrink-0 items-center justify-center rounded-full bg-[#2f2f2f]",
                        isShifted ? "h-6 w-6" : "h-7 w-7"
                      )}>
                        <Sparkles className={cn("text-white", isShifted ? "h-3 w-3" : "h-3.5 w-3.5")} />
                      </div>
                    )}
                    <div
                      className={cn(
                        "rounded-2xl",
                        isShifted ? "max-w-[85%] px-4 py-2.5" : "max-w-[75%] px-4 py-2.5",
                        message.sender === "user" 
                          ? "bg-[#2f2f2f] text-white" 
                          : "bg-transparent text-[#ececec]",
                      )}
                    >
                      <p className={cn("leading-relaxed", isShifted ? "text-[15px]" : "text-[14px]")}>{message.text}</p>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>

            <div className={cn("border-t border-[#3f3f3f] bg-[#212121]", isShifted ? "px-3 py-2.5" : "px-3 py-3")}>
              <div className="relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder={isShifted ? "Tune your scenario to make it more personalized" : "Type your response..."}
                  className={cn(
                    "w-full rounded-[20px] border-0 bg-[#2f2f2f] text-white placeholder:text-[#8e8e8e] focus:outline-none",
                    isShifted ? "px-4 py-3 pr-11 text-[15px]" : "px-4 py-2.5 pr-11 text-[14px]"
                  )}
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim()}
                  className={cn(
                    "absolute right-2 top-1/2 -translate-y-1/2 items-center justify-center rounded-full transition-all",
                    isShifted ? "flex h-8 w-8" : "flex h-7 w-7",
                    input.trim()
                      ? "bg-white text-black hover:bg-white/90"
                      : "bg-[#676767] text-[#8e8e8e]",
                  )}
                >
                  <ArrowUp className={cn("strokeWidth-[2.5]", isShifted ? "h-[17px] w-[17px]" : "h-[16px] w-[16px]")} strokeWidth={2.5} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Loading Animation - справа с анимацией */}
      {step === "generating" && !showMainContent && (
        <div className="fixed right-8 top-1/2 -translate-y-1/2 z-40 animate-in slide-in-from-right duration-700">
          <div className="rounded-xl border border-gray-700/50 bg-gray-900/95 backdrop-blur-sm p-8 shadow-2xl w-[420px]">
            <div className="mb-6 flex flex-col items-center gap-4 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-orange-500 to-orange-600 shadow-lg shadow-orange-500/30">
                <Sparkles className="h-7 w-7 animate-pulse text-white" />
              </div>
              <h3 className="text-xl font-semibold text-white">Generating Scenario</h3>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-center py-8">
                <div className="relative h-16 w-16">
                  <div className="absolute inset-0 rounded-full border-4 border-gray-700"></div>
                  <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-orange-500"></div>
                </div>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-800">
                <div
                  className="h-full w-2/3 animate-pulse rounded-full bg-gradient-to-r from-orange-500 to-orange-400 transition-all duration-1000"
                  style={{ animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite" }}
                />
              </div>
              <p className="text-center text-sm text-gray-400">
                Creating a personalized practice scenario based on your responses...
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Success Animation - когда готово */}
      {showSuccessMessage && (
        <div className="fixed right-8 top-1/2 -translate-y-1/2 z-50 animate-in zoom-in fade-in duration-500">
          <div className="rounded-xl border border-green-500/50 bg-gray-900/95 backdrop-blur-sm p-8 shadow-2xl w-[420px]">
            <div className="flex flex-col items-center gap-4 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-green-500 to-green-600 shadow-lg shadow-green-500/30 animate-pulse">
                <svg className="h-7 w-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white">Scenario Ready!</h3>
              <p className="text-sm text-gray-400">Your personalized practice scenario is ready to start</p>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

