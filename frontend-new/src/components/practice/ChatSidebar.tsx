import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Sparkles, Menu, X, ArrowLeft } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatSidebarProps {
  scenario: string;
  onScenarioChange: (scenario: string) => void;
  onGenerate: () => void;
  onReady: () => void;
}

const ChatSidebar = ({ scenario, onScenarioChange, onGenerate, onReady }: ChatSidebarProps) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Welcome! Tell me about the conversation you'd like to practice. For example: 'I need to pitch my startup to a VC' or 'I want to negotiate a raise with my boss'.",
    },
  ]);
  const [input, setInput] = useState("");
  const [questionCount, setQuestionCount] = useState(0);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    
    if (questionCount === 0) {
      onScenarioChange(input);
    }
    
    setInput("");

    // Ask follow-up questions
    setTimeout(() => {
      if (questionCount === 0) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Got it! What's your main goal for this conversation? What would success look like?",
          },
        ]);
        setQuestionCount(1);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Excellent! I'm now generating your practice scenario and persona...",
          },
        ]);
        onGenerate();
        
        // Simulate generation time
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: "Your scenario is ready! Click the 'Begin Practice' button to start your conversation.",
            },
          ]);
          onReady();
        }, 3000);
      }
    }, 1000);
  };

  return (
    <aside className={`border-r border-border bg-card flex flex-col transition-all duration-300 ${isCollapsed ? 'w-14' : 'w-96'}`}>
      {/* Collapsed State - Just Hamburger */}
      {isCollapsed ? (
        <div className="flex flex-col items-center py-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => setIsCollapsed(false)}
            className="mb-2"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      ) : (
        <>
          {/* Header */}
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Button 
                  variant="ghost" 
                  size="icon"
                  asChild
                >
                  <Link to="/">
                    <ArrowLeft className="h-4 w-4" />
                  </Link>
                </Button>
                <Sparkles className="h-5 w-5 text-primary" />
                <h2 className="text-lg font-semibold">Conversation Coach</h2>
              </div>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => setIsCollapsed(true)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              Setup your practice scenario
            </p>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-4 py-2 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          {/* Input */}
          <div className="p-4 border-t border-border">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Describe your scenario..."
                className="flex-1"
              />
              <Button type="submit" size="icon" disabled={!input.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </>
      )}
    </aside>
  );
};

export default ChatSidebar;
