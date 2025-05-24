import { useTrackTranscription, useVoiceAssistant } from "@livekit/components-react";
import { useMemo, useState, useEffect } from "react";
import useLocalMicTrack from "./useLocalMicTrack";

export type TranscriptionSegment = {
  id: string;
  text: string;
  role: "assistant" | "user" | "system";
  firstReceivedTime: number;
  isFinal: boolean;
}

export default function useCombinedTranscriptions() {
  const { agentTranscriptions } = useVoiceAssistant();
  const [systemMessages, setSystemMessages] = useState<TranscriptionSegment[]>([]);

  const micTrackRef = useLocalMicTrack();
  const { segments: userTranscriptions } = useTrackTranscription(micTrackRef);

  const combinedTranscriptions = useMemo(() => {
    return [
      ...agentTranscriptions.map((val) => {
        return { ...val, role: "assistant" };
      }),
      ...userTranscriptions.map((val) => {
        return { ...val, role: "user" };
      }),
      ...systemMessages,
    ].sort((a, b) => a.firstReceivedTime - b.firstReceivedTime);
  }, [agentTranscriptions, userTranscriptions, systemMessages]);

  // Expose a method to add system messages
  const addSystemMessage = (text: string) => {
    const newMessage: TranscriptionSegment = {
      id: `system-${Date.now()}`,
      text,
      role: "system",
      firstReceivedTime: Date.now(),
      isFinal: true
    };
    setSystemMessages(prev => [...prev, newMessage]);
  };

  return { 
    combinedTranscriptions, 
    addSystemMessage 
  };
}
