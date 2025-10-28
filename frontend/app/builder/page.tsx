"use client"

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"

export default function BuilderPage() {
  return (
    <ResizablePanelGroup
      direction="horizontal"
      className="h-full w-full"
    >
      <ResizablePanel defaultSize={50} minSize={20}>
        <div className="flex h-full items-center justify-center p-6">
          <div className="space-y-4 text-center">
            <h2 className="text-2xl font-semibold">Left Panel</h2>
            <p className="text-muted-foreground">
              This is the left section of the builder.
            </p>
          </div>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={50} minSize={20}>
        <div className="flex h-full items-center justify-center p-6">
          <div className="space-y-4 text-center">
            <h2 className="text-2xl font-semibold">Right Panel</h2>
            <p className="text-muted-foreground">
              This is the right section of the builder.
            </p>
          </div>
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}
