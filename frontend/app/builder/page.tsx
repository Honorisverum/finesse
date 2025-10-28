"use client";

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { ChatPanel } from "@/features/builder/components/chat-panel";

export default function BuilderPage() {
  return (
    <ResizablePanelGroup direction="horizontal">
      {/* Left Panel - Chat */}
      <ResizablePanel defaultSize={50} minSize={20} className="flex flex-col">
        <div className="flex-1 overflow-auto space-y-4">
          <ChatPanel />
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      {/* Right Panel */}
      <ResizablePanel defaultSize={50} minSize={20} className="flex flex-col">
        {/* Fixed header */}
        <Card className="rounded-none border-0 border-b">
          <CardHeader>
            <CardTitle>Right Panel</CardTitle>
          </CardHeader>
        </Card>
        {/* Scrollable content */}
        <div className="flex-1 overflow-auto p-6 space-y-4">
          {Array.from({ length: 11 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <CardTitle>Card {i + 1}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  This is the right section of the builder.
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
