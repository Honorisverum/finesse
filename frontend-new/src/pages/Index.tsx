import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { MessageSquare, Sparkles, Target, Send } from "lucide-react";
import ConversationCard from "@/components/ConversationCard";

const Index = () => {
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      navigate("/practice");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-hero">
      {/* Hero Section */}
      <main className="container mx-auto px-6 pt-24 pb-32">
        <div className="max-w-3xl mx-auto text-center">
          {/* Animated Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-8 animate-fade-in">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">AI-Powered Practice</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-5xl md:text-7xl font-bold mb-6 animate-fade-in" style={{ animationDelay: "0.1s" }}>
            Practice conversations
            <br />
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              before they happen
            </span>
          </h1>

          {/* Description */}
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto animate-fade-in" style={{ animationDelay: "0.2s" }}>
            Pitch to investors. Negotiate with your boss. Prepare for difficult conversations.
            Describe your scenario and practice with an AI persona tailored to your goal.
          </p>

          {/* Chat Input */}
          <form onSubmit={handleSubmit} className="animate-fade-in mb-16" style={{ animationDelay: "0.3s" }}>
            <div className="relative max-w-2xl mx-auto">
              <Input
                type="text"
                placeholder="Describe your conversation scenario..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="h-14 pr-14 text-base border-2 focus-visible:ring-primary"
              />
              <Button
                type="submit"
                size="icon"
                variant="hero"
                className="absolute right-1 top-1 h-12 w-12"
                disabled={!message.trim()}
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
          </form>

          {/* Feature Pills */}
          <div className="flex flex-wrap items-center justify-center gap-8 animate-fade-in" style={{ animationDelay: "0.4s" }}>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MessageSquare className="h-4 w-4 text-primary" />
              <span>Custom personas</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Target className="h-4 w-4 text-primary" />
              <span>Goal-oriented practice</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              <span>Performance scoring</span>
            </div>
          </div>
        </div>
      </main>

      {/* Dashboard Section */}
      <section className="container mx-auto px-6 pb-20 pt-16">
        <div className="max-w-6xl mx-auto">
          {/* Try these */}
          <div className="mb-10">
            <h2 className="text-2xl font-bold mb-4">Try these</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <ConversationCard
              title="Practice interviewing"
              description="Prepare for your next job interview with realistic practice scenarios"
              icon="👔"
              messageCount="2.7k"
            />
            <ConversationCard
              title="Pitch to investors"
              description="Perfect your startup pitch and handle tough investor questions"
              icon="💼"
              messageCount="1.2k"
            />
            <ConversationCard
              title="Negotiate salary"
              description="Build confidence negotiating compensation with your manager"
              icon="💰"
              messageCount="3.4k"
            />
            <ConversationCard
              title="Difficult conversations"
              description="Practice handling confrontation and delivering tough feedback"
              icon="💬"
              messageCount="5.1k"
            />
            <ConversationCard
              title="Sales calls"
              description="Sharpen your sales pitch and objection handling skills"
              icon="📞"
              messageCount="1.8k"
            />
            <ConversationCard
              title="Performance review"
              description="Prepare to discuss your achievements and career goals"
              icon="📊"
              messageCount="2.3k"
            />
            <ConversationCard
              title="Networking events"
              description="Practice making connections and memorable introductions"
              icon="🤝"
              messageCount="987"
            />
            <ConversationCard
              title="Customer support"
              description="Handle difficult customer situations with professionalism"
              icon="🎧"
              messageCount="1.5k"
            />
          </div>
        </div>

        {/* Recent Conversations */}
        <div>
          <h2 className="text-2xl font-bold mb-4">Recent conversations</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <ConversationCard
              title="VC Pitch Practice"
              description="Practiced pitching startup idea to skeptical venture capitalist"
              icon="🚀"
              messageCount="24 messages"
            />
            <ConversationCard
              title="Salary Negotiation"
              description="Negotiated 20% raise with hiring manager at tech company"
              icon="💵"
              messageCount="18 messages"
            />
            <ConversationCard
              title="Conflict Resolution"
              description="Addressed team conflict with senior colleague"
              icon="⚖️"
              messageCount="31 messages"
            />
            <ConversationCard
              title="Interview Prep"
              description="Senior software engineer position at Fortune 500 company"
              icon="💻"
              messageCount="42 messages"
            />
          </div>
        </div>
      </div>
      </section>
    </div>
  );
};

export default Index;
