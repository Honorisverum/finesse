import { useState } from "react";
import ChatSidebar from "@/components/practice/ChatSidebar";
import VoiceVisualizer from "@/components/practice/VoiceVisualizer";
import InfoSidebar from "@/components/practice/InfoSidebar";

type PracticeState = "setup" | "generating" | "ready" | "active";

const Practice = () => {
  const [scenario, setScenario] = useState("");
  const [practiceState, setPracticeState] = useState<PracticeState>("setup");

  const showInfoSidebar = practiceState === "ready" || practiceState === "active";

  return (
    <div className="flex h-screen w-full bg-background">
      <ChatSidebar 
        scenario={scenario} 
        onScenarioChange={setScenario}
        onGenerate={() => setPracticeState("generating")}
        onReady={() => setPracticeState("ready")}
      />
      <main className="flex-1 flex items-center justify-center p-8">
        <VoiceVisualizer 
          practiceState={practiceState}
          onStart={() => setPracticeState("active")}
        />
      </main>
      {showInfoSidebar && <InfoSidebar scenario={scenario} />}
    </div>
  );
};

export default Practice;
