"use client";

import { CloseIcon } from "@/components/CloseIcon";
import { NoAgentNotification } from "@/components/NoAgentNotification";
import TranscriptionView from "@/components/TranscriptionView";
import HintPanel from "@/components/HintPanel";
import GoalProgressPanel from "@/components/GoalProgressPanel";
import PostAnalyzerPanel, { PostAnalyzerData } from "@/components/PostAnalyzerPanel";
import OnboardingChat from "@/components/OnboardingChat";
import {
  BarVisualizer,
  DisconnectButton,
  RoomAudioRenderer,
  RoomContext,
  VideoTrack,
  VoiceAssistantControlBar,
  useVoiceAssistant,
  useRoomContext,
} from "@livekit/components-react";
import { AnimatePresence, motion } from "framer-motion";
import { Room, RoomEvent } from "livekit-client";
import { useCallback, useEffect, useState, useContext } from "react";
import type { ConnectionDetails } from "./api/connection-details/route";
import type { Skill, Scenario, HintData, GoalProgressData } from "@/utils/types";

export default function Page() {
  const [room] = useState(new Room());
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<string>("");
  const [selectedScenario, setSelectedScenario] = useState<string>("");
  const [userName, setUserName] = useState<string>("Vlad");
  const [userGender, setUserGender] = useState<string>("male");
  const [chosenOptions, setChosenOptions] = useState(false);
  const [hint, setHint] = useState<HintData | null>(null);
  const [goalProgress, setGoalProgress] = useState<GoalProgressData | null>(null);
  const [analysisResult, setAnalysisResult] = useState<PostAnalyzerData | null>(null);
  const [showAnalysisResults, setShowAnalysisResults] = useState(false);
  const [attemptCount, setAttemptCount] = useState(0);
  const [emojiReactions, setEmojiReactions] = useState<Array<{id: number, emoji: string}>>([]);
  const [showOnboarding, setShowOnboarding] = useState(true);
  const [onboardingData, setOnboardingData] = useState<{skill: string, aspects: string, pitfalls: string} | null>(null);
  const [generatedScenarios, setGeneratedScenarios] = useState<any[]>([]);
  const [isLoadingScenarios, setIsLoadingScenarios] = useState(false);

  // Загрузка скиллов и сценариев при монтировании компонента
  useEffect(() => {
    const fetchSkills = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/scenarios');
        
        if (!response.ok) {
          throw new Error(`Error fetching scenarios: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.skills && data.skills.length > 0) {
          setSkills(data.skills);
          // Устанавливаем первый скилл и сценарий по умолчанию
          setSelectedSkill(data.skills[0].name);
          if (data.skills[0].scenarios.length > 0) {
            setSelectedScenario(data.skills[0].scenarios[0].id);
          }
        } else {
          setError('No skills or scenarios found');
        }
      } catch (err) {
        console.error('Failed to fetch scenarios:', err);
        setError('Failed to load skills and scenarios');
      } finally {
        setLoading(false);
      }
    };

    fetchSkills();
  }, []);

  // Регистрация RPC методов для проверки прогресса к цели и получения анализа
  useEffect(() => {
    if (room) {
      // Регистрация RPC метода для проверки прогресса к цели
      room.registerRpcMethod('checker', async (data) => {
        try {
          console.log('Received checker RPC call', data);
          
          // Парсим данные точно как указано
          const payload = JSON.parse(data.payload);
          
          // Обновляем состояние
          setGoalProgress(payload);
          
          return 'ok';
        } catch (error) {
          console.error('Error processing checker data', error);
          return 'error';
        }
      });
      
      // Регистрация RPC метода для эмоджи реакций
      room.registerRpcMethod('reaction', async (data: { payload: string }) => {
        try {
          console.log('Received reaction RPC call', data);
          
          const emoji = data.payload;
          const id = Date.now();
          
          setEmojiReactions((prev: Array<{id: number, emoji: string}>) => [...prev, { id, emoji }]);
          
          // Удаляем эмоджи через 3 секунды
          setTimeout(() => {
            setEmojiReactions((prev: Array<{id: number, emoji: string}>) => prev.filter((e: {id: number, emoji: string}) => e.id !== id));
          }, 3000);
          
          return 'ok';
        } catch (error) {
          console.error('Error processing reaction data', error);
          return 'error';
        }
      });
      
      // Очистка при размонтировании
      return () => {
        room.unregisterRpcMethod('checker');
        room.unregisterRpcMethod('reaction');
      };
    }
  }, [room]);

  const onConnectButtonClicked = useCallback(async () => {
    if (!selectedSkill || !selectedScenario) {
      console.error('No skill or scenario selected');
      return;
    }

    // Reset progress state when starting a new call
    setGoalProgress(null);

    // Находим выбранный сценарий
    const selectedScenarioData = generatedScenarios.length > 0
      ? generatedScenarios.find(s => s.id === selectedScenario)
      : skills.find(skill => skill.name === selectedSkill)?.scenarios.find(s => s.id === selectedScenario);

    if (!selectedScenarioData) {
      console.error('Selected scenario data not found');
      return;
    }

    // Generate room connection details
    const url = new URL(
      "/api/connection-details",
      window.location.origin
    );
    
    // Передаем полную информацию о сценарии (без картинки) и user info
    const { image_base64, ...scenarioInfo } = selectedScenarioData;
    url.searchParams.append("scenarioData", JSON.stringify(scenarioInfo));
    url.searchParams.append("userName", userName || "Vlad");
    url.searchParams.append("userGender", userGender);
    console.log('Sending full scenario data to livekit (without image):', scenarioInfo);
    
    const response = await fetch(url.toString());
    const connectionDetailsData: ConnectionDetails = await response.json();

    await room.connect(connectionDetailsData.serverUrl, connectionDetailsData.participantToken);
    await room.localParticipant.setMicrophoneEnabled(true);
  }, [room, selectedSkill, selectedScenario, userName, userGender, generatedScenarios, skills]);

  useEffect(() => {
    room.on(RoomEvent.MediaDevicesError, onDeviceFailure);

    return () => {
      room.off(RoomEvent.MediaDevicesError, onDeviceFailure);
    };
  }, [room]);

  const handleOnboardingComplete = async (chatHistory: Array<{role: string, content: string}>) => {
    setIsLoadingScenarios(true);
    
    try {
      // Вызываем API для получения сценариев
      const response = await fetch('https://belyaev-vladislav-nw--finesse-scenario-selector-get-scenarios.modal.run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ chat_history: chatHistory }),
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Received scenarios from API:', data);
      
      // Сохраняем полученные сценарии
      setGeneratedScenarios(data.scenarios);
      setSelectedSkill(data.skill);
      
      // Автоматически выбираем первый сценарий
      if (data.scenarios.length > 0) {
        setSelectedScenario(data.scenarios[0].id);
      }
      
      setShowOnboarding(false);
    } catch (error) {
      console.error('Failed to fetch scenarios:', error);
      // Fallback: используем существующую логику
      if (skills.length > 0) {
        const randomSkill = skills[Math.floor(Math.random() * skills.length)];
        setSelectedSkill(randomSkill.name);
        console.log(`Fallback: выбран скилл ${randomSkill.name}`);
        
        if (randomSkill.scenarios.length > 0) {
          setSelectedScenario(randomSkill.scenarios[0].id);
        }
      }
      setShowOnboarding(false);
    } finally {
      setIsLoadingScenarios(false);
    }
  };

  return (
    <main data-lk-theme="default" className="h-screen w-screen overflow-hidden bg-[var(--lk-bg)] relative">
      <RoomContext.Provider value={room}>
        {/* Personal Info - всегда справа вверху */}
        <div className="fixed top-3 right-3 z-[60] flex items-center gap-3">
          {/* Name input */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-[#8e8e8e] font-medium px-1">Name</label>
            <input
              type="text"
              placeholder="Vlad"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              className="w-32 px-3 py-1.5 bg-[#2f2f2f] border border-[#3f3f3f] rounded-lg text-[13px] text-white placeholder:text-[#6e6e6e] focus:outline-none focus:border-[#5f5f5f] transition-colors"
            />
          </div>
          
          {/* Gender selector */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-[#8e8e8e] font-medium px-1">Gender</label>
            <div className="flex items-center gap-1 bg-[#2f2f2f] border border-[#3f3f3f] rounded-lg p-0.5">
              <button
                onClick={() => setUserGender("male")}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  userGender === "male" 
                    ? "bg-white text-black shadow-sm" 
                    : "bg-transparent text-[#ececec] hover:text-white"
                }`}
              >
                Male
              </button>
              <button
                onClick={() => setUserGender("female")}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  userGender === "female" 
                    ? "bg-white text-black shadow-sm" 
                    : "bg-transparent text-[#ececec] hover:text-white"
                }`}
              >
                Female
              </button>
              <button
                onClick={() => setUserGender("neutral")}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  userGender === "neutral" 
                    ? "bg-white text-black shadow-sm" 
                    : "bg-transparent text-[#ececec] hover:text-white"
                }`}
              >
                Neutral
              </button>
            </div>
          </div>
        </div>

        {/* Onboarding Chat */}
        <OnboardingChat 
          onComplete={handleOnboardingComplete} 
          showMainContent={!showOnboarding}
        />

        {/* Main Content - появляется справа после onboarding */}
        {!showOnboarding && (
          <div className="fixed right-0 top-0 bottom-0 w-[calc(100vw-450px)] pt-24 px-8 overflow-y-auto animate-in fade-in slide-in-from-right duration-700">
            {loading ? (
              <div className="text-center py-8">Loading skills and scenarios...</div>
            ) : error ? (
              <div className="text-center text-red-500 py-8">{error}</div>
            ) : (
              <SimpleVoiceAssistant 
              onConnectButtonClicked={onConnectButtonClicked}
              skills={skills}
              selectedSkill={selectedSkill}
              setSelectedSkill={setSelectedSkill}
              selectedScenario={selectedScenario}
              setSelectedScenario={setSelectedScenario}
              userName={userName}
              setUserName={setUserName}
              userGender={userGender}
              setUserGender={setUserGender}
              chosenOptions={chosenOptions}
              setChosenOptions={setChosenOptions}
              hint={hint}
              setHint={setHint}
              goalProgress={goalProgress}
              setGoalProgress={setGoalProgress}
              analysisResult={analysisResult}
              setAnalysisResult={setAnalysisResult}
              showAnalysisResults={showAnalysisResults}
              setShowAnalysisResults={setShowAnalysisResults}
              attemptCount={attemptCount}
              setAttemptCount={setAttemptCount}
              emojiReactions={emojiReactions}
              setEmojiReactions={setEmojiReactions}
              generatedScenarios={generatedScenarios}
            />
          )}
          </div>
        )}
      </RoomContext.Provider>
    </main>
  );
}

function SimpleVoiceAssistant(props: { 
  onConnectButtonClicked: () => void,
  skills: Skill[],
  selectedSkill: string,
  setSelectedSkill: (skill: string) => void,
  selectedScenario: string,
  setSelectedScenario: (scenario: string) => void,
  userName: string,
  setUserName: (userName: string) => void,
  userGender: string,
  setUserGender: (userGender: string) => void,
  chosenOptions: boolean,
  setChosenOptions: (chosen: boolean) => void,
  hint: HintData | null,
  setHint: (hint: HintData | null) => void,
  goalProgress: GoalProgressData | null,
  setGoalProgress: (goalProgress: GoalProgressData | null) => void,
  analysisResult: PostAnalyzerData | null,
  setAnalysisResult: (analysisResult: PostAnalyzerData | null) => void,
  showAnalysisResults: boolean,
  setShowAnalysisResults: (show: boolean) => void,
  attemptCount: number,
  setAttemptCount: (attemptCount: number) => void,
  emojiReactions: Array<{id: number, emoji: string}>,
  setEmojiReactions: (reactions: Array<{id: number, emoji: string}> | ((prev: Array<{id: number, emoji: string}>) => Array<{id: number, emoji: string}>)) => void,
  generatedScenarios: any[]
}) {
  const { state: agentState } = useVoiceAssistant();
  const roomContext = useRoomContext();
  const [isConnected, setIsConnected] = useState(false);
  const [showHintPanel, setShowHintPanel] = useState(false);
  const [showHintButton, setShowHintButton] = useState(false);
  const [isProcessingAnalysis, setIsProcessingAnalysis] = useState(false);
  const [showAnalysisPreparing, setShowAnalysisPreparing] = useState(false);
  const [endConversationMessage, setEndConversationMessage] = useState<string | null>(null);
  const [showRoleplay, setShowRoleplay] = useState(false);
  const [roleplayText, setRoleplayText] = useState<string | null>(null);
  const [scenarioDescription, setScenarioDescription] = useState<string | null>(null);
  const [selectedScenarioName, setSelectedScenarioName] = useState<string | null>(null);
  const [scenarioGoal, setScenarioGoal] = useState<string | null>(null);
  const [emojiReactions, setEmojiReactions] = useState<Array<{id: number, emoji: string}>>([]);
  
  // Инициализируем описание и цель первого сценария
  useEffect(() => {
    const currentSkill = props.skills.find(skill => skill.name === props.selectedSkill);
    if (currentSkill && currentSkill.scenarios.length > 0) {
      const firstScenario = currentSkill.scenarios.find(s => s.id === props.selectedScenario);
      if (firstScenario) {
        setSelectedScenarioName(firstScenario.name);
        setScenarioDescription(firstScenario.description);
        setScenarioGoal(firstScenario.goal);
      }
    }
  }, [props.selectedSkill, props.selectedScenario, props.skills]);
  
  useEffect(() => {
    console.log('Agent state changed to:', agentState);
    
    if (agentState !== 'disconnected') {
      setIsConnected(true);
    } else {
      setIsConnected(false);
      setShowHintButton(false);
    }
  }, [agentState]);
  
  // Split opening into roleplay and script
  const splitOpening = (text: string) => {
    const roleplayMatch = text.match(/(\*[^*]*\*)/);
    if (!roleplayMatch) {
      return ['', text.trim()];
    }
    const roleplay = roleplayMatch[1];
    const script = text.replace(roleplay, '').trim();
    return [roleplay, script];
  };

  // Handle connect button with roleplay display
  const handleConnect = async () => {
    try {
      // Find the selected scenario
      const currentSkill = props.skills.find(skill => skill.name === props.selectedSkill);
      if (!currentSkill) return;
      
      const scenario = currentSkill.scenarios.find(s => s.id === props.selectedScenario);
      if (!scenario) return;
      
      // Fetch the scenario details to get the opening text
      const response = await fetch(`/api/scenario-detail?skill=${props.selectedSkill}&id=${props.selectedScenario}`);
      
      if (response.ok) {
        const data = await response.json();
        if (data.opening) {
          const [roleplay, _] = splitOpening(data.opening);
          if (roleplay) {
            setRoleplayText(roleplay);
            setShowRoleplay(true);
            
            // Wait 5 seconds then connect
            setTimeout(() => {
              setShowRoleplay(false);
              props.onConnectButtonClicked();
              
              // Add the roleplay text to the transcription after the connection is established
              setTimeout(() => {
                // Dispatch a custom event to add the roleplay text to the transcription
                const event = new CustomEvent('add-system-message', { 
                  detail: { message: roleplay } 
                });
                document.dispatchEvent(event);
              }, 1000); // Wait a bit for the connection to establish
            }, 5000);
            
            return;
          }
        }
      }
      
      // If we couldn't get the opening or there's no roleplay, just connect directly
      props.onConnectButtonClicked();
    } catch (error) {
      console.error('Failed to process opening:', error);
      props.onConnectButtonClicked();
    }
  };

  // Показываем кнопку через 10 секунд после начала звонка
  useEffect(() => {
    // Если мы не на экране выбора опций (звонок начался)
    if (agentState !== "disconnected") {
      console.log('Call started, scheduling hint button');
      
      // Устанавливаем таймер на 10 секунд
      const timer = setTimeout(() => {
        console.log('Showing hint button after 10 seconds');
        setShowHintButton(true);
      }, 10000);
      
      // Очищаем таймер при размонтировании
      return () => {
        console.log('Clearing timer');
        clearTimeout(timer);
      };
    } else {
      // Сбрасываем состояние при отключении
      setShowHintButton(false);
    }
    // Зависимость только от ПЕРВОГО перехода в не-disconnected состояние
  }, [agentState === "disconnected"]);
  
  // Функция для запроса хинта
  const requestHint = async () => {
    try {
      if (!roomContext || !roomContext.localParticipant) {
        console.error('Room or local participant not available');
        return;
      }
      
      const serverParticipant = roomContext.remoteParticipants.keys().next().value;
      if (!serverParticipant) {
        console.error('No remote participants found');
        return;
      }
      
      const response = await roomContext.localParticipant.performRpc({
        destinationIdentity: serverParticipant,
        method: 'hint',
        payload: 'hint request',
      });
      
      console.log('Hint request response:', response);
      
      setShowHintPanel(true);
      
      try {
        const hintData = JSON.parse(response);
        props.setHint(hintData);
      } catch (error) {
        console.error('Failed to parse hint response:', error);
      }
    } catch (error) {
      console.error('Failed to request hint:', error);
    }
  };

  // Функция для запроса анализа
  const requestAnalysis = async () => {
    if (isProcessingAnalysis) {
      console.log("Already processing analysis, ignoring request");
      return;
    }
    
    setIsProcessingAnalysis(true);
    setShowAnalysisPreparing(true);
    console.log("Starting analysis process");
    
    try {
      if (!roomContext || !roomContext.localParticipant) {
        console.error('Room or local participant not available');
        setIsProcessingAnalysis(false);
        setShowAnalysisPreparing(false);
        return;
      }
      
      const serverParticipant = roomContext.remoteParticipants.keys().next().value;
      if (!serverParticipant) {
        console.error('No remote participants found');
        setIsProcessingAnalysis(false);
        setShowAnalysisPreparing(false);
        return;
      }
      
      // Make up to 3 attempts to get analysis
      let analysisData = null;
      const maxAttempts = 3;
      let currentAttempt = 0;
      
      while (currentAttempt < maxAttempts && !analysisData) {
        currentAttempt++;
        props.setAttemptCount(currentAttempt);
        try {
          console.log(`Calling postanalyzer RPC (attempt ${currentAttempt}/${maxAttempts})`);
          
          const response = await roomContext.localParticipant.performRpc({
            destinationIdentity: serverParticipant,
            method: 'postanalyzer',
            payload: 'analysis request',
          });
          
          console.log(`Analysis response received (attempt ${currentAttempt}/${maxAttempts}):`, response);
          
          try {
            analysisData = JSON.parse(response);
            console.log("Successfully parsed response, updating state", analysisData);
          } catch (error) {
            console.error('Failed to parse analysis response:', error);
            if (currentAttempt < maxAttempts) {
              console.log(`Waiting before next attempt (${currentAttempt}/${maxAttempts})...`);
              // Wait 2 seconds before the next attempt
              await new Promise(resolve => setTimeout(resolve, 2000));
            }
          }
        } catch (error) {
          console.error(`Failed to request analysis (attempt ${currentAttempt}/${maxAttempts}):`, error);
          if (currentAttempt < maxAttempts) {
            console.log(`Waiting before next attempt (${currentAttempt}/${maxAttempts})...`);
            // Wait 2 seconds before the next attempt
            await new Promise(resolve => setTimeout(resolve, 2000));
          }
        }
      }
      
      if (analysisData) {
        props.setAnalysisResult(analysisData);
        props.setShowAnalysisResults(true);
        setShowAnalysisPreparing(false);
      } else {
        console.error('Failed to get analysis after multiple attempts');
        setIsProcessingAnalysis(false);
        setShowAnalysisPreparing(false);
      }
      
      // Now it's safe to disconnect
      console.log("Analysis process complete, disconnecting from room");
      roomContext.disconnect();
    } catch (error) {
      console.error('Failed to process analysis:', error);
      setIsProcessingAnalysis(false);
      setShowAnalysisPreparing(false);
      
      // If we failed to get the analysis, still disconnect
      console.log("Analysis failed, still disconnecting from room");
      roomContext.disconnect();
    }
  };

  // Register client RPC method for end_conversation
  useEffect(() => {
    if (roomContext) {
      roomContext.registerRpcMethod('end_conversation', async (data: { payload: string }) => {
        try {
          console.log('Received end_conversation RPC call', data);
          
          // Parse data
          const payload = JSON.parse(data.payload);
          const message = payload.message;
          
          // Set the message to display
          setEndConversationMessage(message);
          
          // Start analysis process
          await requestAnalysis();
          
          return 'ok';
        } catch (error) {
          console.error('Error processing end_conversation data', error);
          return 'error';
        }
      });
      
      // Cleanup
      return () => {
        roomContext.unregisterRpcMethod('end_conversation');
      };
    }
  }, [roomContext, requestAnalysis]);

  const currentSkill = props.skills.find(skill => skill.name === props.selectedSkill) || props.skills[0];
  
  // Используем сгенерированные сценарии если они есть, иначе берем из существующих
  const scenarios = props.generatedScenarios.length > 0 
    ? props.generatedScenarios 
    : (currentSkill?.scenarios || []);

  const handleScenarioClick = (scenario: any) => {
    props.setSelectedScenario(scenario.id);
    setSelectedScenarioName(scenario.name || scenario.title);
    setScenarioDescription(scenario.description);
    setScenarioGoal(scenario.goal);
    console.log("Selected scenario:", scenario);
    console.log("Goal:", scenario.goal);
  };

  return (
    <>
      <AnimatePresence mode="wait">
        {props.showAnalysisResults && props.analysisResult ? (
          <motion.div
            key="analysis-results"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 p-4 overflow-y-auto"
          >
            <PostAnalyzerPanel 
              data={props.analysisResult} 
              onClose={() => {
                console.log("Closing analysis results");
                props.setShowAnalysisResults(false);
                props.setAnalysisResult(null);
                setIsProcessingAnalysis(false);
                setShowAnalysisPreparing(false);
                setEndConversationMessage(null);
                props.setAttemptCount(0);
              }}
            />
          </motion.div>
        ) : showAnalysisPreparing ? (
          <motion.div
            key="analysis-preparing"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 p-4"
          >
            <div className="bg-gray-800 rounded-lg p-8 max-w-md w-full text-center">
              <h2 className="text-2xl font-bold mb-4">Analysis is preparing...</h2>
              <div className="flex justify-center my-6">
                <svg className="w-12 h-12 animate-spin" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <p className="text-gray-300">We're analyzing your performance.</p>
              {props.attemptCount > 0 && (
                <p className="text-gray-400 text-sm mt-2">Attempt {props.attemptCount}/3</p>
              )}
              {endConversationMessage && (
                <p className="text-white mt-4 p-3 bg-gray-700 rounded-md">{endConversationMessage}</p>
              )}
              <p className="text-gray-300 mt-2">This may take a moment...</p>
            </div>
          </motion.div>
        ) : showRoleplay ? (
          <motion.div
            key="roleplay"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 p-4"
          >
            <div className="bg-gray-800 rounded-lg p-8 max-w-lg w-full text-center">
              <div className="text-xl font-light my-6">{roleplayText}</div>
            </div>
          </motion.div>
        ) : agentState === "disconnected" ? (
          <motion.div
            key="disconnected"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="grid items-center justify-center h-full"
          >
            {!props.chosenOptions ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="flex flex-col gap-4 bg-gray-800 p-6 rounded-lg w-full max-w-3xl"
              >
                <h2 className="text-xl font-bold text-center mb-2">Choose Scenario</h2>
                <p className="text-sm text-gray-400 text-center mb-2">
                  Skill: <span className="text-white font-semibold">{props.selectedSkill}</span>
                </p>
                
                {/* Выбор сценария */}
                {(
                  <div className="w-full">
                    <div className="grid grid-cols-4 gap-3">
                      {scenarios.map((scenario) => {
                        // Используем base64 изображение если есть, иначе путь к файлу
                        const imageSource = scenario.image_base64 
                          ? `data:image/png;base64,${scenario.image_base64}`
                          : `/photos/${props.selectedSkill.toLowerCase().replace(/\s+/g, '')}/${scenario.id}.png`;
                        
                        const scenarioName = scenario.name || scenario.title;
                        
                        return (
                          <button
                            key={scenario.id}
                            onClick={() => handleScenarioClick(scenario)}
                            className={`relative rounded-xl overflow-hidden h-48 ${
                              props.selectedScenario === scenario.id 
                                ? "ring-4 ring-white shadow-lg" 
                                : "ring-1 ring-gray-600 hover:ring-2 hover:ring-gray-400"
                            }`}
                          >
                            <img 
                              src={imageSource} 
                              alt={scenarioName}
                              className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black to-transparent opacity-70"></div>
                            <div className="absolute bottom-0 left-0 right-0 p-3">
                              <p className="text-white font-semibold text-sm">{scenarioName}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                    
                    {/* Описание и цель выбранного сценария */}
                    {scenarioDescription && (
                      <div className="mt-4 p-4 bg-gray-700 rounded-xl shadow-inner">
                        <p className="text-sm text-gray-300">{scenarioDescription}</p>
                        
                        {/* Всегда показываем блок с целью */}
                        <div className="mt-3 pt-3 border-t border-gray-600">
                          <div className="flex items-center">
                            <div className="bg-yellow-600 w-4 h-4 rounded-full mr-2"></div>
                            <p className="text-sm font-semibold text-white">goal:</p>
                          </div>
                          <p className="text-sm text-yellow-300 mt-1 px-2 py-1 bg-gray-800 rounded">{scenarioGoal}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Кнопка Start Call */}
                <div className="flex justify-center mt-4">
                  <button
                    className="px-6 py-3 bg-white text-black rounded-md font-semibold hover:bg-gray-200 transition-colors"
                    onClick={handleConnect}
                  >
                    Start Call
                  </button>
                </div>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="flex flex-col items-center gap-4"
              >
                <div className="bg-gray-800 p-4 rounded-lg text-center mb-4">
                  <p className="text-lg font-bold">{props.selectedSkill}</p>
                  <p className="text-sm mt-1">{
                    scenarios.find(s => s.id === props.selectedScenario)?.name || props.selectedScenario
                  }</p>
                  <p className="text-xs mt-2 text-gray-400 max-w-xs">{
                    scenarios.find(s => s.id === props.selectedScenario)?.description || ''
                  }</p>
                  <div className="mt-3 pt-3 border-t border-gray-600">
                    <p className="text-sm">
                      {props.userName || "Vlad"} ({props.userGender})
                    </p>
                  </div>
                </div>
                
                <motion.button
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3, delay: 0.1 }}
                  className="uppercase px-4 py-2 bg-white text-black rounded-md"
                  onClick={handleConnect}
                >
                  Start a conversation
                </motion.button>
                
                <button
                  className="text-sm text-gray-400 underline mt-2"
                  onClick={() => props.setChosenOptions(false)}
                >
                  Change options
                </button>
              </motion.div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="connected"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="flex flex-col items-center gap-4 h-full"
          >
            <div className="bg-gray-800 py-2 px-4 rounded-full text-sm mb-2 flex items-center gap-3">
              {isProcessingAnalysis && (
                <span className="text-blue-400 animate-pulse flex items-center gap-1">
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing analysis...
                </span>
              )}
              
              {/* Отображение цели во время звонка */}
              {scenarioGoal && !isProcessingAnalysis && (
                <div className="flex items-center">
                  <div className="bg-yellow-600 w-3 h-3 rounded-full mr-2"></div>
                  <span className="text-yellow-300 text-xs mr-1">Goal:</span>
                  <span className="text-white text-xs">{scenarioGoal}</span>
                </div>
              )}
              
              {showHintButton && !isProcessingAnalysis && (
                <div className="relative">
                  <button 
                    onClick={requestHint}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm py-1.5 px-3 rounded-md transition-colors flex items-center gap-1.5 font-medium"
                  >
                    <span role="img" aria-label="refresh">🔁</span>
                    Get hint
                  </button>
                  
                  {/* Hint Panel - compact version */}
                  {showHintPanel && (
                    <div className="absolute top-full mt-2 right-0 w-64 z-10">
                      <HintPanel hint={props.hint} />
                    </div>
                  )}
                </div>
              )}
            </div>
            
            <div className="relative">
              <AgentVisualizer />
              
              {/* Emoji Reactions */}
              <AnimatePresence>
                {props.emojiReactions.map((reaction) => (
                  <motion.div
                    key={reaction.id}
                    initial={{ opacity: 0, scale: 0.5, y: 0 }}
                    animate={{ opacity: 1, scale: 1.5, y: -100 }}
                    exit={{ opacity: 0, scale: 0.5 }}
                    transition={{ duration: 2.5, ease: "easeOut" }}
                    className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-6xl pointer-events-none"
                    style={{
                      left: `${50 + (Math.random() - 0.5) * 40}%`,
                    }}
                  >
                    {reaction.emoji}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
            
            {/* CTA Message display */}
            <AnimatePresence>
              {props.goalProgress?.CTA && (
                <CTAMessage key={props.goalProgress.CTA} message={props.goalProgress.CTA} improved={props.goalProgress.progress_towards_goal >= props.goalProgress.previous_progress_towards_goal} />
              )}
            </AnimatePresence>
            
            {/* Goal Progress Panel */}
            {props.goalProgress && (
              <div className="w-full max-w-2xl my-4">
                <GoalProgressPanel data={props.goalProgress} />
              </div>
            )}
            
            <div className="flex-1 w-full">
              <TranscriptionView />
            </div>
            <div className="w-full">
              <ControlBar 
                onConnectButtonClicked={props.onConnectButtonClicked} 
                setAnalysisResult={props.setAnalysisResult}
                setShowAnalysisResults={props.setShowAnalysisResults}
                setIsProcessingAnalysis={setIsProcessingAnalysis}
                isProcessingAnalysis={isProcessingAnalysis}
                requestAnalysis={requestAnalysis}
                setAttemptCount={props.setAttemptCount}
              />
            </div>
            <RoomAudioRenderer />
            <NoAgentNotification state={agentState} />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function AgentVisualizer() {
  const { state: agentState, videoTrack, audioTrack } = useVoiceAssistant();

  if (videoTrack) {
    return (
      <div className="h-[512px] w-[512px] rounded-lg overflow-hidden">
        <VideoTrack trackRef={videoTrack} />
      </div>
    );
  }
  return (
    <div className="h-[300px] w-full">
      <BarVisualizer
        state={agentState}
        barCount={5}
        trackRef={audioTrack}
        className="agent-visualizer"
        options={{ minHeight: 24 }}
      />
    </div>
  );
}

function ControlBar(props: { 
  onConnectButtonClicked: () => void,
  setAnalysisResult: (result: PostAnalyzerData | null) => void,
  setShowAnalysisResults: (show: boolean) => void,
  setIsProcessingAnalysis: (isProcessing: boolean) => void,
  isProcessingAnalysis: boolean,
  requestAnalysis: () => Promise<void>,
  setAttemptCount: (count: number) => void
}) {
  const { state: agentState } = useVoiceAssistant();
  const roomContext = useRoomContext();
  
  const handleDisconnect = async () => {
    // Prevent multiple clicks
    if (props.isProcessingAnalysis) {
      console.log("Already processing analysis, ignoring click");
      return;
    }
    
    // Reset attempt count
    props.setAttemptCount(0);
    
    // Call the requestAnalysis function to fetch analysis data
    await props.requestAnalysis();
  };

  return (
    <div className="relative h-[60px]">
      <AnimatePresence>
        {agentState === "disconnected" && (
          <motion.button
            initial={{ opacity: 0, top: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, top: "-10px" }}
            transition={{ duration: 1, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="uppercase absolute left-1/2 -translate-x-1/2 px-4 py-2 bg-white text-black rounded-md"
            onClick={() => props.onConnectButtonClicked()}
          >
            Start a conversation
          </motion.button>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {agentState !== "disconnected" && agentState !== "connecting" && (
          <motion.div
            initial={{ opacity: 0, top: "10px" }}
            animate={{ opacity: 1, top: 0 }}
            exit={{ opacity: 0, top: "-10px" }}
            transition={{ duration: 0.4, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="flex h-8 absolute left-1/2 -translate-x-1/2  justify-center"
          >
            <VoiceAssistantControlBar controls={{ leave: false }} />
            <button
              className={`lk-button lk-disconnect-button ${props.isProcessingAnalysis ? 'opacity-50 cursor-not-allowed' : ''}`}
              onClick={handleDisconnect}
              disabled={props.isProcessingAnalysis}
            >
              {props.isProcessingAnalysis ? (
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <CloseIcon />
              )}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function onDeviceFailure(error: Error) {
  console.error(error);
  alert(
    "Error acquiring camera or microphone permissions. Please make sure you grant the necessary permissions in your browser and reload the tab"
  );
}

// Component to display CTA messages prominently
function CTAMessage({ message, improved = true }: { message: string, improved?: boolean }) {
  const [isVisible, setIsVisible] = useState(true);
  
  useEffect(() => {
    // Auto-hide after 3.5 seconds
    const timer = setTimeout(() => {
      setIsVisible(false);
    }, 3500);
    
    return () => clearTimeout(timer);
  }, [message]);
  
  if (!isVisible || !message) return null;
  
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.9 }} 
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none"
    >
      <div className="py-5 px-8 backdrop-blur-sm bg-opacity-40 bg-transparent rounded-lg">
        <p className={`text-3xl font-semibold text-center tracking-wide ${improved ? 'text-green-400' : 'text-red-400'}`}>
          {message}
        </p>
      </div>
    </motion.div>
  );
}

// Функция для получения эмодзи для навыка не нужна, логотипы уже указаны конкретно
function getSkillEmoji(skillName: string): string {
  const emojis: {[key: string]: string} = {
    "Art of Persuasion": "🎯",
    "Attraction": "💘",
    "Conflict Resolution": "🤝",
    "Decoding Emotions": "🔍",
    "Manipulation Defense": "🛡️",
    "Negotiation": "💼",
    "Small Talk": "💬"
  };
  
  return emojis[skillName] || "✨";
}
