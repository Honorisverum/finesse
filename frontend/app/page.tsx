"use client";

import { CloseIcon } from "@/components/CloseIcon";
import { NoAgentNotification } from "@/components/NoAgentNotification";
import TranscriptionView from "@/components/TranscriptionView";
import HintPanel from "@/components/HintPanel";
import GoalProgressPanel from "@/components/GoalProgressPanel";
import PostAnalyzerPanel, { PostAnalyzerData } from "@/components/PostAnalyzerPanel";
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

    // Generate room connection details with skill and scenarioName
    const url = new URL(
      "/api/connection-details",
      window.location.origin
    );
    
    // Add query parameters
    url.searchParams.append("skill", selectedSkill);
    url.searchParams.append("scenarioName", selectedScenario);
    url.searchParams.append("userName", userName || "Vlad");
    url.searchParams.append("userGender", userGender);
    
    const response = await fetch(url.toString());
    const connectionDetailsData: ConnectionDetails = await response.json();

    await room.connect(connectionDetailsData.serverUrl, connectionDetailsData.participantToken);
    await room.localParticipant.setMicrophoneEnabled(true);
  }, [room, selectedSkill, selectedScenario, userName, userGender]);

  useEffect(() => {
    room.on(RoomEvent.MediaDevicesError, onDeviceFailure);

    return () => {
      room.off(RoomEvent.MediaDevicesError, onDeviceFailure);
    };
  }, [room]);

  return (
    <main data-lk-theme="default" className="h-full grid content-center bg-[var(--lk-bg)]">
      <RoomContext.Provider value={room}>
        <div className="lk-room-container max-w-[1024px] w-[90vw] mx-auto max-h-[90vh]">
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
            />
          )}
        </div>
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
  setEmojiReactions: (reactions: Array<{id: number, emoji: string}> | ((prev: Array<{id: number, emoji: string}>) => Array<{id: number, emoji: string}>)) => void
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
  const [currentStep, setCurrentStep] = useState(1); // 1 - имя/гендер, 2 - навык, 3 - сценарий
  const [scenarioDescription, setScenarioDescription] = useState<string | null>(null);
  const [selectedScenarioName, setSelectedScenarioName] = useState<string | null>(null);
  const [scenarioGoal, setScenarioGoal] = useState<string | null>(null);
  const [emojiReactions, setEmojiReactions] = useState<Array<{id: number, emoji: string}>>([]);
  
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
  
  const scenarios = currentSkill.scenarios;
  
  const handleSkillChange = (skillName: string) => {
    props.setSelectedSkill(skillName);
    
    const newSkill = props.skills.find(skill => skill.name === skillName);
    if (newSkill && newSkill.scenarios.length > 0) {
      props.setSelectedScenario(newSkill.scenarios[0].id);
      setSelectedScenarioName(newSkill.scenarios[0].name);
      setScenarioDescription(newSkill.scenarios[0].description);
    }
  };

  const handleScenarioClick = (scenario: Scenario) => {
    props.setSelectedScenario(scenario.id);
    setSelectedScenarioName(scenario.name);
    setScenarioDescription(scenario.description);
    setScenarioGoal(scenario.goal);
    console.log("Selected scenario:", scenario);
    console.log("Goal:", scenario.goal);
  };

  const nextStep = () => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1);
    } else {
      props.setChosenOptions(true);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
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
                <h2 className="text-xl font-bold text-center mb-2">
                  {currentStep === 1 ? "Personal Info" : 
                   currentStep === 2 ? "Select Skill" : "Choose Scenario"}
                </h2>
                
                {/* Шаг 1: Имя и гендер */}
                {currentStep === 1 && (
                  <>
                    <div className="flex flex-col gap-2">
                      <label className="text-sm">Your Name:</label>
                      <input
                        type="text"
                        placeholder="Enter your name (optional)"
                        value={props.userName}
                        onChange={(e) => props.setUserName(e.target.value)}
                        className="px-3 py-2 bg-gray-700 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-white"
                      />
                    </div>
                    
                    <div className="flex flex-col gap-2">
                      <label className="text-sm">Your Gender:</label>
                      <div className="flex gap-2">
                        <button
                          onClick={() => props.setUserGender("male")}
                          className={`flex-1 px-3 py-1 rounded-md text-sm ${
                            props.userGender === "male" 
                              ? "bg-white text-black" 
                              : "bg-gray-700 text-white"
                          }`}
                        >
                          Male
                        </button>
                        <button
                          onClick={() => props.setUserGender("female")}
                          className={`flex-1 px-3 py-1 rounded-md text-sm ${
                            props.userGender === "female" 
                              ? "bg-white text-black" 
                              : "bg-gray-700 text-white"
                          }`}
                        >
                          Female
                        </button>
                        <button
                          onClick={() => props.setUserGender("neutral")}
                          className={`flex-1 px-3 py-1 rounded-md text-sm ${
                            props.userGender === "neutral" 
                              ? "bg-white text-black" 
                              : "bg-gray-700 text-white"
                          }`}
                        >
                          Neutral
                        </button>
                      </div>
                    </div>
                  </>
                )}
                
                {/* Шаг 2: Выбор навыка */}
                {currentStep === 2 && (
                  <div className="w-full">
                    <div className="flex flex-col space-y-3">
                      {props.skills.map((skill) => {
                        // Цвета для каждого навыка
                        const skillColors: {[key: string]: string} = {
                          "artofpersuasion": "bg-gradient-to-r from-blue-800 to-blue-500",
                          "attraction": "bg-gradient-to-r from-pink-800 to-pink-500",
                          "conflictresolution": "bg-gradient-to-r from-orange-800 to-orange-500", 
                          "decodingemotions": "bg-gradient-to-r from-purple-800 to-purple-500",
                          "manipulationdefense": "bg-gradient-to-r from-red-800 to-red-500",
                          "negotiation": "bg-gradient-to-r from-green-800 to-green-500",
                          "smalltalk": "bg-gradient-to-r from-indigo-800 to-indigo-500"
                        };
                        
                        const bgColor = skillColors[skill.name.toLowerCase().replace(/\s+/g, '')];
                        
                        // Конкретные логотипы для скиллов как SVG
                        const skillLogos: {[key: string]: JSX.Element} = {
                          "artofpersuasion": (
                            <svg className="w-9 h-9 text-white" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
                            </svg>
                          ),
                          "attraction": (
                            <svg className="w-9 h-9 text-white" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
                            </svg>
                          ),
                          "conflictresolution": (
                            <svg className="w-9 h-9 text-white" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M21 6h-2v9H6v2c0 .55.45 1 1 1h11l4 4V7c0-.55-.45-1-1-1zm-4 6V3c0-.55-.45-1-1-1H3c-.55 0-1 .45-1 1v14l4-4h10c.55 0 1-.45 1-1z"/>
                            </svg>
                          ),
                          "decodingemotions": (
                            <svg className="w-9 h-9 text-white" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M9 11.75c-.69 0-1.25.56-1.25 1.25s.56 1.25 1.25 1.25 1.25-.56 1.25-1.25-.56-1.25-1.25-1.25zm6 0c-.69 0-1.25.56-1.25 1.25s.56 1.25 1.25 1.25 1.25-.56 1.25-1.25-.56-1.25-1.25-1.25zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8 0-.29.02-.58.05-.86 2.36-1.05 4.23-2.98 5.21-5.37C11.07 8.33 14.05 10 17.42 10c.78 0 1.53-.09 2.25-.26.21.71.33 1.47.33 2.26 0 4.41-3.59 8-8 8z"/>
                            </svg>
                          ),
                          "manipulationdefense": (
                            <svg className="w-9 h-9 text-white" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/>
                            </svg>
                          ),
                          "negotiation": (
                            <svg className="w-9 h-9 text-white" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z"/>
                            </svg>
                          ),
                          "smalltalk": (
                            <svg className="w-9 h-9 text-white" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/>
                            </svg>
                          )
                        };
                        
                        return (
                          <button
                            key={skill.name}
                            onClick={() => handleSkillChange(skill.name)}
                            className={`relative rounded-xl overflow-hidden shadow-lg transform transition-all duration-200 w-full ${
                              props.selectedSkill === skill.name 
                                ? "scale-[1.02] ring-2 ring-white" 
                                : "hover:scale-[1.01] hover:brightness-110"
                            }`}
                          >
                            <div className={`flex items-center p-4 ${bgColor} h-24`}>
                              <div className="flex-shrink-0 bg-black bg-opacity-30 w-16 h-16 rounded-full flex items-center justify-center mr-4">
                                {skillLogos[skill.name.toLowerCase().replace(/\s+/g, '')]}
                              </div>
                              <div className="flex-1">
                                <h3 className="text-xl font-bold text-white">{skill.name}</h3>
                              </div>
                              {props.selectedSkill === skill.name && (
                                <div className="ml-3 bg-white bg-opacity-20 p-2 rounded-full">
                                  <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                  </svg>
                                </div>
                              )}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
                
                {/* Шаг 3: Выбор сценария */}
                {currentStep === 3 && (
                  <div className="w-full">
                    <div className="grid grid-cols-4 gap-3">
                      {scenarios.map((scenario) => {
                        // Путь к фото
                        const imagePath = `/photos/${props.selectedSkill.toLowerCase().replace(/\s+/g, '')}/${scenario.id}.png`;
                        
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
                              src={imagePath} 
                              alt={scenario.name}
                              className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black to-transparent opacity-70"></div>
                            <div className="absolute bottom-0 left-0 right-0 p-3">
                              <p className="text-white font-semibold text-sm">{scenario.name}</p>
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
                
                {/* Навигационные кнопки */}
                <div className="flex justify-between mt-4">
                  {currentStep > 1 ? (
                    <button
                      className="px-4 py-2 bg-gray-700 text-white rounded-md"
                      onClick={prevStep}
                    >
                      Back
                    </button>
                  ) : <div></div>}
                  
                  <button
                    className="px-4 py-2 bg-white text-black rounded-md"
                    onClick={currentStep === 3 ? handleConnect : nextStep}
                  >
                    {currentStep === 3 ? "Start Call" : "Next"}
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
