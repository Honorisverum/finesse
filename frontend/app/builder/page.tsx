"use client";

import { useState } from "react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { ChatPanel } from "@/features/builder/components/chat-panel";
import { ScenarioDisplay } from "@/features/builder/components/scenario-display";

type ScenarioData = {
  context: string;
  persona: {
    name: string;
    role: string;
    traits: string;
  };
  objections: string[];
};

export default function BuilderPage() {
  const [scenarioData, setScenarioData] = useState<ScenarioData | undefined>();

  return (
    <ResizablePanelGroup direction="horizontal">
      {/* Left Panel - Chat */}
      <ResizablePanel defaultSize={50} minSize={20} className="flex flex-col">
        <ChatPanel onScenarioGenerated={setScenarioData} />
      </ResizablePanel>

      <ResizableHandle withHandle />

      {/* Right Panel - Scenario Display */}
      <ResizablePanel defaultSize={50} minSize={20} className="flex flex-col">
        <ScenarioDisplay data={scenarioData} />
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
