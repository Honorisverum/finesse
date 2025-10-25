import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Mic, MicOff } from "lucide-react";
type PracticeState = "setup" | "generating" | "ready" | "active";
interface VoiceVisualizerProps {
  practiceState: PracticeState;
  onStart: () => void;
}
const VoiceVisualizer = ({
  practiceState,
  onStart
}: VoiceVisualizerProps) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevels, setAudioLevels] = useState<number[]>(new Array(50).fill(0));
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  useEffect(() => {
    if (practiceState === "active" && isRecording) {
      // Simulate audio levels for visualization
      const interval = setInterval(() => {
        setAudioLevels(prev => {
          const newLevels = [...prev.slice(1)];
          newLevels.push(Math.random() * 0.8 + 0.2);
          return newLevels;
        });
      }, 50);
      return () => clearInterval(interval);
    }
  }, [practiceState, isRecording]);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const draw = () => {
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      // Draw sine wave
      ctx.beginPath();
      ctx.strokeStyle = "hsl(var(--primary))";
      ctx.lineWidth = 3;
      const barWidth = width / audioLevels.length;
      const centerY = height / 2;
      audioLevels.forEach((level, index) => {
        const x = index * barWidth;
        const amplitude = level * centerY * 0.8;
        const y = centerY + Math.sin(index / audioLevels.length * Math.PI * 4) * amplitude;
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.stroke();
      animationRef.current = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [audioLevels]);
  const toggleRecording = () => {
    setIsRecording(!isRecording);
    if (!isRecording) {
      setAudioLevels(new Array(50).fill(0));
    }
  };
  const handleBeginPractice = () => {
    onStart();
    setIsRecording(true);
  };

  // Setup state - waiting for chat
  if (practiceState === "setup") {
    return <div className="flex flex-col items-center gap-8 w-full max-w-4xl">
        <div className="w-full border border-border rounded-2xl p-12 shadow-lg">
          <div className="text-center space-y-4">
            <h3 className="text-2xl font-semibold text-muted-foreground">
              Describe your scenario in the chat
            </h3>
            <p className="text-sm text-muted-foreground">
              Tell me what conversation you'd like to practice
            </p>
          </div>
        </div>
      </div>;
  }

  // Generating state - loading
  if (practiceState === "generating") {
    return <div className="flex flex-col items-center gap-8 w-full max-w-4xl">
        <div className="w-full bg-card border border-border rounded-2xl p-8 shadow-lg">
          <div className="space-y-4">
            <Skeleton className="w-full h-48" />
          </div>
        </div>
        <div className="text-center space-y-2">
          <h3 className="text-2xl font-semibold">Generating your scenario...</h3>
          <p className="text-sm text-muted-foreground">
            Creating a custom persona and conversation flow
          </p>
        </div>
      </div>;
  }

  // Ready state - show begin button
  if (practiceState === "ready") {
    return <div className="flex flex-col items-center gap-8 w-full max-w-4xl">
        <div className="w-full bg-card border border-border rounded-2xl p-8 shadow-lg">
          <canvas ref={canvasRef} width={800} height={200} className="w-full h-48 opacity-30" />
        </div>

        <div className="text-center space-y-2">
          <h3 className="text-2xl font-semibold">Your scenario is ready!</h3>
          <p className="text-sm text-muted-foreground">
            Click below to begin your practice conversation
          </p>
        </div>

        <Button size="lg" variant="hero" className="h-16 px-12 text-lg" onClick={handleBeginPractice}>
          Begin Practice
        </Button>
      </div>;
  }

  // Active state - recording interface
  return <div className="flex flex-col items-center gap-8 w-full max-w-4xl">
      <div className="w-full bg-card border border-border rounded-2xl p-8 shadow-lg">
        <canvas ref={canvasRef} width={800} height={200} className="w-full h-48" />
      </div>

      <div className="text-center space-y-2">
        <p className="text-sm text-muted-foreground">
          {isRecording ? "Listening..." : "Ready when you are"}
        </p>
        <h3 className="text-2xl font-semibold">
          {isRecording ? "Speak naturally" : "Click to speak"}
        </h3>
      </div>

      <Button size="lg" variant={isRecording ? "destructive" : "hero"} className="h-20 w-20 rounded-full" onClick={toggleRecording}>
        {isRecording ? <MicOff className="h-8 w-8" /> : <Mic className="h-8 w-8" />}
      </Button>
    </div>;
};
export default VoiceVisualizer;