import { CloseIcon } from "./CloseIcon";
import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

// Type for postanalyzer data
export type PostAnalyzerData = {
  complete_score: string;
  radar_diagram: {
    impact: {
      score: number;
      insight: string;
    };
    rapport: {
      score: number;
      insight: string;
    };
    flex: {
      score: number;
      insight: string;
    };
    frame: {
      score: number;
      insight: string;
    };
    timing: {
      score: number;
      insight: string;
    };
  };
  feedback: string[];
  overall_message: string;
};

interface PostAnalyzerPanelProps {
  data: PostAnalyzerData;
  onClose: () => void;
}

// SVG Icons for each skill
const SkillIcons = {
  impact: (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" className="text-yellow-300">
      <path d="M12 1L9 9H2L7 14.5L5 22L12 17.5L19 22L17 14.5L22 9H15L12 1Z" />
    </svg>
  ),
  rapport: (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" className="text-blue-300">
      <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM8 17.5C7.17 17.5 6.5 16.83 6.5 16C6.5 15.17 7.17 14.5 8 14.5C8.83 14.5 9.5 15.17 9.5 16C9.5 16.83 8.83 17.5 8 17.5ZM9.5 8C9.5 7.17 10.17 6.5 11 6.5C11.83 6.5 12.5 7.17 12.5 8C12.5 8.83 11.83 9.5 11 9.5C10.17 9.5 9.5 8.83 9.5 8ZM12 13C10.62 13 9.5 11.88 9.5 10.5C9.5 9.12 10.62 8 12 8C13.38 8 14.5 9.12 14.5 10.5C14.5 11.88 13.38 13 12 13ZM14.5 16C14.5 15.17 15.17 14.5 16 14.5C16.83 14.5 17.5 15.17 17.5 16C17.5 16.83 16.83 17.5 16 17.5C15.17 17.5 14.5 16.83 14.5 16Z"/>
    </svg>
  ),
  flex: (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" className="text-green-300">
      <path d="M19 8L15 12H18C18 15.31 15.31 18 12 18C10.99 18 10.03 17.75 9.2 17.3L7.74 18.76C8.97 19.54 10.43 20 12 20C16.42 20 20 16.42 20 12H23L19 8ZM6 12C6 8.69 8.69 6 12 6C13.01 6 13.97 6.25 14.8 6.7L16.26 5.24C15.03 4.46 13.57 4 12 4C7.58 4 4 7.58 4 12H1L5 16L9 12H6Z"/>
    </svg>
  ),
  frame: (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" className="text-purple-300">
      <path d="M3 3V21H21V3H3ZM19 19H5V5H19V19ZM8 17H16V15H8V17ZM16 13H8V11H16V13ZM8 9H16V7H8V9Z"/>
    </svg>
  ),
  timing: (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" className="text-red-300">
      <path d="M12 2C6.5 2 2 6.5 2 12C2 17.5 6.5 22 12 22C17.5 22 22 17.5 22 12C22 6.5 17.5 2 12 2ZM16.2 16.2L11 13V7H12.5V12.2L17 14.9L16.2 16.2Z"/>
    </svg>
  )
};

// Confetti Component
const Confetti = ({ isActive }: { isActive: boolean }) => {
  if (!isActive) return null;
  
  const colors = ['#FFD700', '#FF6B6B', '#4CAF50', '#5D8BF4', '#FF8A65', '#BA68C8'];
  const pieces = Array.from({ length: 60 }, (_, i) => i + 1);
  
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-10">
      {pieces.map(piece => {
        const size = Math.floor(Math.random() * 15) + 5;
        const color = colors[Math.floor(Math.random() * colors.length)];
        const left = Math.random() * 100;
        const animationDuration = (Math.random() * 3) + 2;
        const delay = Math.random() * 0.5;
        
        return (
          <motion.div
            key={piece}
            initial={{ 
              top: '30%', 
              left: `${left}%`, 
              width: size, 
              height: size, 
              backgroundColor: color,
              opacity: 1,
              rotate: 0
            }}
            animate={{ 
              top: '120%', 
              opacity: 0,
              rotate: 360,
              x: Math.random() * 200 - 100 
            }}
            transition={{ 
              duration: animationDuration,
              delay,
              ease: [0.1, 0.4, 0.8, 1] 
            }}
            className="absolute rounded-sm"
          />
        );
      })}
    </div>
  );
};

// Single Skill Highlight Component
function SkillHighlight({ 
  skillName, 
  score, 
  insight, 
  icon, 
  color 
}: { 
  skillName: string; 
  score: number; 
  insight: string; 
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <motion.div 
      className="flex flex-col items-center justify-center p-6 h-[280px]"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
      key={`skill-highlight-${skillName}`}
    >
      <div className="mb-4 flex flex-col items-center">
        <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-2 ${color}`}>
          <div className="w-10 h-10 flex items-center justify-center">
            {icon}
          </div>
        </div>
        <h3 className="text-2xl font-bold text-white">{skillName}</h3>
      </div>
      
      <div className="w-full max-w-xs mb-6">
        <div className="flex justify-between mb-1">
          <span className="text-gray-300 text-sm">Score</span>
          <span className="text-white font-medium">{score}/10</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2.5">
          <motion.div 
            className={`h-2.5 rounded-full ${color}`}
            initial={{ width: "0%" }}
            animate={{ width: `${score * 10}%` }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            key={`skill-bar-${skillName}`}
          />
        </div>
      </div>
      
      <div className="bg-[#2A2F42] p-4 rounded-lg max-w-xs">
        <p className="text-white text-sm text-center">{insight}</p>
      </div>
    </motion.div>
  );
}

// Radar Chart Component
function RadarChart({ 
  data, 
  onSelectSkill, 
  shouldAnimate, 
  activeRadarPoint 
}: { 
  data: PostAnalyzerData['radar_diagram'], 
  onSelectSkill: (skill: string, insight: string) => void,
  shouldAnimate: boolean,
  activeRadarPoint: number
}) {
  // Center point and radius
  const centerX = 160;
  const centerY = 160;
  const radius = 138;
  
  // Calculate positions for exact pentagon corners (72° apart)
  const getPointCoordinates = (index: number) => {
    const angle = (Math.PI / 180) * ((-90) + (index * 72)); // Start from top (-90°) and go clockwise (72° = 360/5)
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    };
  };
  
  // Create the five points of the pentagon
  const skillKeys = ['impact', 'rapport', 'flex', 'timing', 'frame'];
  
  const points = skillKeys.map((key, index) => ({
    key,
    label: key === 'flex' ? 'Flexibility' : key === 'frame' ? 'Framing' : key.charAt(0).toUpperCase() + key.slice(1),
    icon: SkillIcons[key as keyof typeof SkillIcons],
    score: data[key as keyof typeof data].score,
    ...getPointCoordinates(index)
  }));
  
  // Calculate points for each score on the radar
  const getScorePoint = (point: typeof points[0], scoreRatio: number = 1) => {
    return {
      x: centerX + (point.x - centerX) * (point.score / 10) * scoreRatio,
      y: centerY + (point.y - centerY) * (point.score / 10) * scoreRatio
    };
  };
  
  // Get color for each skill
  const getSkillColor = (skill: string) => {
    switch(skill) {
      case 'impact': return '#EAB308';
      case 'rapport': return '#3B82F6';
      case 'flex': return '#22C55E';
      case 'timing': return '#EF4444';
      case 'frame': return '#A855F7';
      default: return '#94A3B8';
    }
  };

  // Draw guidelines with same logic
  const getGuidelinePath = (ratio: number) => {
    return points.map((point, i) => {
      const x = centerX + (point.x - centerX) * ratio;
      const y = centerY + (point.y - centerY) * ratio;
      return `${i === 0 ? 'M' : 'L'}${x},${y}`;
    }).join(' ') + 'Z';
  };

  // Calculate visible points based on animation progress
  const visiblePoints = activeRadarPoint === -1 
    ? points 
    : points.slice(0, activeRadarPoint + 1);
  
  // Create partial radar path for animation
  const radarPath = visiblePoints.length <= 1 
    ? '' 
    : visiblePoints.map((point, i) => {
        const scorePoint = getScorePoint(point, 1);
        return `${i === 0 ? 'M' : 'L'}${scorePoint.x},${scorePoint.y}`;
      }).join(' ') + (visiblePoints.length < points.length ? '' : 'Z');

  // Рассчитаем позиции цифр, расположенных вдоль радиальной линии
  const getScoreTextPosition = (point: typeof points[0]) => {
    // Вычисляем угол от центра к точке
    const angle = Math.atan2(point.y - centerY, point.x - centerX);
    // Размещаем цифру дальше на 20px от иконки вдоль той же линии
    const distance = 40; // Увеличенное расстояние от центра иконки
    
    // Определяем выравнивание текста в зависимости от угла
    let anchor = "middle";
    if (point.x < centerX - 30) anchor = "end"; // левая сторона
    else if (point.x > centerX + 30) anchor = "start"; // правая сторона
    
    // Определяем дополнительное смещение для лучшей видимости
    let offsetX = 0;
    let offsetY = 0;
    
    // Специальные корректировки для конкретных углов
    // Для правой верхней части (Rapport)
    if (point.x > centerX && point.y < centerY) {
      offsetX = 8;
      offsetY = -8;
    }
    // Для левой нижней части (Timing)
    else if (point.x < centerX && point.y > centerY) {
      offsetX = -8;
      offsetY = 0;
    }
    
    return {
      x: point.x + Math.cos(angle) * distance + offsetX,
      y: point.y + Math.sin(angle) * distance + offsetY,
      anchor: anchor
    };
  };

  return (
    <div className="relative w-[320px] h-[310px] mx-auto pt-0 mt-0">
      <motion.svg 
        width="320" 
        height="310" 
        viewBox="-40 -40 380 380"
        initial={shouldAnimate ? { opacity: 0 } : { opacity: 1 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        {/* Определения для переиспользования */}
        <defs>
          {/* Определяем точки скора для переиспользования */}
          {points.map((point, index) => {
            const scorePoint = getScorePoint(point);
            return (
              <circle 
                key={`point-def-${point.key}`}
                id={`score-point-${point.key}`}
                cx={scorePoint.x} 
                cy={scorePoint.y} 
                r="3" 
                fill="#FFFFFF"
              />
            );
          })}
        </defs>
        
        {/* Background pentagon */}
        <path 
          d={points.map((point, i) => 
            `${i === 0 ? 'M' : 'L'}${point.x},${point.y}`
          ).join(' ') + 'Z'}
          fill="none"
          stroke="#4B5563"
          strokeWidth="1"
          strokeDasharray="3,3"
        />
        
        {/* Inner guidelines */}
        <path 
          d={getGuidelinePath(0.75)}
          fill="none"
          stroke="#4B5563"
          strokeWidth="0.5"
          strokeDasharray="2,2"
        />
        
        <path 
          d={getGuidelinePath(0.5)}
          fill="none"
          stroke="#4B5563"
          strokeWidth="0.5"
          strokeDasharray="2,2"
        />
        
        <path 
          d={getGuidelinePath(0.25)}
          fill="none"
          stroke="#4B5563"
          strokeWidth="0.5"
          strokeDasharray="2,2"
        />
        
        {/* Radar chart filled area */}
        <motion.path 
          d={radarPath}
          fill="rgba(59, 130, 246, 0.3)"
          stroke="#3B82F6"
          strokeWidth="2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        />
        
        {/* Score lines for each point */}
        {visiblePoints.map((point, index) => {
          const scorePoint = getScorePoint(point);
          return (
            <motion.line
              key={`line-${point.key}`}
              x1={centerX}
              y1={centerY}
              x2={scorePoint.x}
              y2={scorePoint.y}
              stroke={getSkillColor(point.key)}
              strokeWidth="1.5"
              strokeDasharray="2,2"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.8, delay: index * 0.2 }}
            />
          );
        })}
        
        {/* Score points */}
        {visiblePoints.map((point, index) => (
          <motion.use
            key={`point-${point.key}`}
            href={`#score-point-${point.key}`}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.3 + index * 0.2, duration: 0.3 }}
          />
        ))}
        
        {/* Skill icons */}
        {points.map((point, index) => (
          <motion.g 
            key={`icon-${point.key}`} 
            className="cursor-pointer" 
            onClick={() => onSelectSkill(
              point.key, 
              data[point.key as keyof typeof data]?.insight || ''
            )}
            filter="drop-shadow(0px 2px 2px rgba(0, 0, 0, 0.3))"
            initial={{ opacity: 0, y: 10 }}
            animate={{ 
              opacity: 1, 
              y: 0, 
              scale: activeRadarPoint === index ? 1.1 : 1
            }}
            transition={{ delay: 0.2 + index * 0.1, duration: 0.3 }}
            whileHover={{ scale: 1.1 }}
          >
            {/* Background circle for icon */}
            <circle 
              cx={point.x} 
              cy={point.y} 
              r="22" 
              fill="#374151" 
              stroke={activeRadarPoint === index ? getSkillColor(point.key) : "#6B7280"} 
              strokeWidth={activeRadarPoint === index ? "2" : "1"}
            />
            {/* Icon */}
            <foreignObject
              x={point.x - 12}
              y={point.y - 12}
              width="24"
              height="24"
            >
              <div className="flex items-center justify-center h-full">
                {point.icon}
              </div>
            </foreignObject>

            {/* Skill label */}
            <text 
              x={point.x} 
              y={point.y + 35} 
              textAnchor="middle" 
              fill="#D1D5DB"
              fontSize="12"
              fontWeight="medium"
            >
              {point.label}
            </text>
          </motion.g>
        ))}
        
        {/* Верхний слой со значениями (будет отображаться поверх всех других элементов) */}
        <g className="score-labels-overlay">
          {points.map((point, index) => {
            // Вычисляем угол от центра к точке
            const angle = Math.atan2(point.y - centerY, point.x - centerX);
            
            // Увеличенное расстояние от центра иконки до цифры - вдоль радиальной линии
            const distance = 45;
            
            // Рассчитываем позицию цифры точно вдоль линии от центра к точке
            const labelX = centerX + Math.cos(angle) * (radius + distance);
            const labelY = centerY + Math.sin(angle) * (radius + distance);
            
            return (
              <motion.g 
                key={`score-label-${point.key}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 + index * 0.1 }}
              >
                {/* Более заметный фоновый круг для цифры */}
                <circle 
                  cx={labelX} 
                  cy={labelY} 
                  r="11" 
                  fill="rgba(0, 0, 0, 0.85)" 
                  stroke={getSkillColor(point.key)}
                  strokeWidth="2"
                />
                {/* Сама цифра */}
                <text 
                  x={labelX} 
                  y={labelY} 
                  textAnchor="middle"
                  dominantBaseline="middle" 
                  fill="#FFFFFF"
                  fontSize="16"
                  fontWeight="bold"
                >
                  {point.score}
                </text>
              </motion.g>
            );
          })}
        </g>
      </motion.svg>
    </div>
  );
}

export default function PostAnalyzerPanel({ data, onClose }: PostAnalyzerPanelProps) {
  // UI state
  const [selectedSkill, setSelectedSkill] = useState<{name: string, insight: string} | null>(null);
  const [shouldAnimate, setShouldAnimate] = useState(true);
  const [animationComplete, setAnimationComplete] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  
  // Animation sequence states
  const [showSkillIntro, setShowSkillIntro] = useState(true);
  const [activeSkillIndex, setActiveSkillIndex] = useState(0);
  const [showRadarChart, setShowRadarChart] = useState(false);
  const [activeRadarPoint, setActiveRadarPoint] = useState(-1);
  const [feedbackAnimationStarted, setFeedbackAnimationStarted] = useState(false);
  const [activeFeedbackIndex, setActiveFeedbackIndex] = useState(-1);
  const [scoreAnimationStarted, setScoreAnimationStarted] = useState(false);
  const [messageAnimationStarted, setMessageAnimationStarted] = useState(false);
  
  const autoInsightTimer = useRef<NodeJS.Timeout | null>(null);
  
  // Debug output when component mounts
  useEffect(() => {
    console.log("Overall message:", data.overall_message);
    console.log("Feedback:", data.feedback);
  }, [data]);
  
  // Define the order of skills to be displayed
  const skillOrder = ['impact', 'rapport', 'flex', 'timing', 'frame'];
  
  // Get color class for a skill
  const getSkillColor = (skill: string) => {
    switch(skill) {
      case 'impact': return 'bg-yellow-600';
      case 'rapport': return 'bg-blue-600';
      case 'flex': return 'bg-green-600';
      case 'timing': return 'bg-red-600';
      case 'frame': return 'bg-purple-600';
      default: return 'bg-gray-600';
    }
  };
  
  // Manage skill intro sequence
  useEffect(() => {
    if (!shouldAnimate || !showSkillIntro) return;
    
    // Show each skill for 3 seconds
    if (activeSkillIndex < skillOrder.length) {
      const timer = setTimeout(() => {
        setActiveSkillIndex(activeSkillIndex + 1);
      }, 3000);
      
      return () => clearTimeout(timer);
    } else if (activeSkillIndex >= skillOrder.length) {
      // All skills have been shown, now show the radar chart
      setShowSkillIntro(false);
      setShowRadarChart(true);
      
      // Start radar points animation immediately
      setActiveRadarPoint(0);
      
      return () => {};
    }
  }, [activeSkillIndex, skillOrder.length, shouldAnimate, showSkillIntro]);
  
  // Manage radar point animation
  useEffect(() => {
    if (!showRadarChart || activeRadarPoint === -1) return;
    
    if (activeRadarPoint < skillOrder.length) {
      // Show each radar point every second
      const timer = setTimeout(() => {
        setActiveRadarPoint(activeRadarPoint + 1);
      }, 1000);
      
      return () => clearTimeout(timer);
    } else {
      // When radar is complete, start feedback animation
      const timer = setTimeout(() => {
        setFeedbackAnimationStarted(true);
        setActiveFeedbackIndex(0);
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [showRadarChart, activeRadarPoint, skillOrder.length]);
  
  // Auto-hide insight after 3 seconds
  useEffect(() => {
    if (selectedSkill) {
      if (autoInsightTimer.current) {
        clearTimeout(autoInsightTimer.current);
      }
      
      autoInsightTimer.current = setTimeout(() => {
        setSelectedSkill(null);
      }, 3000);
    }
    
    return () => {
      if (autoInsightTimer.current) {
        clearTimeout(autoInsightTimer.current);
      }
    };
  }, [selectedSkill]);
  
  // Manage sequential feedback display
  useEffect(() => {
    if (!feedbackAnimationStarted) return;
    
    if (activeFeedbackIndex >= 0 && activeFeedbackIndex < data.feedback.length) {
      // Display each feedback for 3 seconds
      const feedbackTimer = setTimeout(() => {
        setActiveFeedbackIndex(activeFeedbackIndex + 1);
      }, 3000);
      
      return () => clearTimeout(feedbackTimer);
    } else if (activeFeedbackIndex >= data.feedback.length && !scoreAnimationStarted) {
      // Start score animation after all feedbacks have been shown
      setScoreAnimationStarted(true);
      
      // Show confetti when score appears
      setShowConfetti(true);
      const confettiTimer = setTimeout(() => {
        setShowConfetti(false);
      }, 3000);
      
      return () => clearTimeout(confettiTimer);
    }
  }, [activeFeedbackIndex, data.feedback.length, scoreAnimationStarted, feedbackAnimationStarted]);
  
  // Trigger message animation after score animation
  useEffect(() => {
    if (scoreAnimationStarted && !messageAnimationStarted) {
      console.log("Starting message animation timer");
      const messageTimer = setTimeout(() => {
        console.log("Setting messageAnimationStarted to true");
        setMessageAnimationStarted(true);
      }, 1500);
      
      return () => clearTimeout(messageTimer);
    }
  }, [scoreAnimationStarted, messageAnimationStarted]);
  
  useEffect(() => {
    // Set animation complete after all animations finish
    if (messageAnimationStarted) {
      const completeTimer = setTimeout(() => {
        setAnimationComplete(true);
      }, 1500);
      
      return () => clearTimeout(completeTimer);
    }
  }, [messageAnimationStarted]);
  
  const handleSelectSkill = (skill: string, insight: string) => {
    setSelectedSkill({ name: skill, insight });
  };
  
  const restartAnimation = () => {
    setAnimationComplete(false);
    setFeedbackAnimationStarted(false);
    setActiveFeedbackIndex(-1);
    setScoreAnimationStarted(false);
    setMessageAnimationStarted(false);
    setShowConfetti(false);
    setShowSkillIntro(true);
    setActiveSkillIndex(0);
    setShowRadarChart(false);
    setActiveRadarPoint(-1);
    setShouldAnimate(false);
    setTimeout(() => {
      setShouldAnimate(true);
    }, 50);
  };

  // Effects for the complete score animation
  const scoreVariants = {
    hidden: { opacity: 0, scale: 0.8 },
    initial: { 
      opacity: 1, 
      scale: 3,
      filter: "blur(0px)",
      y: -20
    },
    final: { 
      scale: 1,
      y: 0,
      filter: "blur(0px)",
      opacity: 1,
      transition: {
        type: "spring",
        damping: 10,
        stiffness: 100,
        duration: 1.5
      }
    }
  };

  // Get current skill data for intro
  const getCurrentSkillData = () => {
    if (activeSkillIndex >= skillOrder.length) return null;
    
    const skillKey = skillOrder[activeSkillIndex];
    const skillData = data.radar_diagram[skillKey as keyof typeof data.radar_diagram];
    
    let skillName = skillKey.charAt(0).toUpperCase() + skillKey.slice(1);
    if (skillKey === 'flex') skillName = 'Flexibility';
    if (skillKey === 'frame') skillName = 'Framing';
    
    return {
      name: skillName,
      key: skillKey,
      score: skillData.score,
      insight: skillData.insight,
      icon: SkillIcons[skillKey as keyof typeof SkillIcons],
      color: getSkillColor(skillKey)
    };
  };

  const currentSkill = getCurrentSkillData();

  // Debug logs
  console.log(`Animation states:
  - showSkillIntro: ${showSkillIntro}
  - activeSkillIndex: ${activeSkillIndex}
  - showRadarChart: ${showRadarChart}
  - feedbackAnimationStarted: ${feedbackAnimationStarted}
  - activeFeedbackIndex: ${activeFeedbackIndex}
  - scoreAnimationStarted: ${scoreAnimationStarted}
  - messageAnimationStarted: ${messageAnimationStarted}
  `);

  return (
    <div className="bg-[#1A1E2A] rounded-lg p-5 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      <Confetti isActive={showConfetti} />
      
      <div className="flex justify-end mb-0 absolute top-3 right-5 z-50">
        <motion.button
          onClick={restartAnimation}
          className="flex items-center justify-center w-10 h-10 rounded-full bg-indigo-600 text-white font-bold text-sm shadow-lg border-2 border-white"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          title="Restart animation"
        >
          RE
        </motion.button>
      </div>

      <div className="flex flex-col items-center mt-0 pt-0">
        {/* Radar Chart Section with skill intro animation */}
        <motion.div 
          className="mb-2 w-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center mb-1">
            <h3 className="text-lg font-semibold text-left pl-3 pt-0 mt-0">Your Unique Style (click icons for more)</h3>
          </div>
          
          <div className="relative">
            {/* Skill Intro Animation */}
            <AnimatePresence mode="wait">
              {showSkillIntro && currentSkill && (
                <SkillHighlight
                  key={`skill-intro-${currentSkill.name}`}
                  skillName={currentSkill.name}
                  score={currentSkill.score}
                  insight={currentSkill.insight}
                  icon={currentSkill.icon}
                  color={currentSkill.color}
                />
              )}
            </AnimatePresence>
            
            {/* Radar Chart */}
            {showRadarChart && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
              >
                <RadarChart 
                  data={data.radar_diagram} 
                  onSelectSkill={handleSelectSkill} 
                  shouldAnimate={shouldAnimate}
                  activeRadarPoint={activeRadarPoint}
                />
                
                {/* Skill insight popup - directly attached to the radar chart */}
                <AnimatePresence>
                  {selectedSkill && (
                    <motion.div 
                      key={selectedSkill.name}
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 5 }}
                      transition={{ duration: 0.3 }}
                      className="absolute left-0 right-0 top-[260px] mx-auto max-w-[280px] p-3 bg-[#2A2F42] rounded-lg shadow-lg border border-[#3A3F52]"
                    >
                      <h4 className="text-blue-300 capitalize font-medium mb-1 flex items-center gap-2 text-sm">
                        {selectedSkill.name === 'impact' && SkillIcons.impact}
                        {selectedSkill.name === 'rapport' && SkillIcons.rapport}
                        {selectedSkill.name === 'flex' && SkillIcons.flex}
                        {selectedSkill.name === 'frame' && SkillIcons.frame}
                        {selectedSkill.name === 'timing' && SkillIcons.timing}
                        {selectedSkill.name === 'impact' ? 'Impact' : 
                          selectedSkill.name === 'rapport' ? 'Rapport' :
                          selectedSkill.name === 'flex' ? 'Flexibility' :
                          selectedSkill.name === 'frame' ? 'Framing' : 'Timing'}
                      </h4>
                      <p className="text-white text-xs">{selectedSkill.insight}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Feedback Section */}
        {(showRadarChart || feedbackAnimationStarted) && (
          <motion.div 
            className="mb-4 w-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: feedbackAnimationStarted ? 1 : 0 }}
            transition={{ duration: 0.5 }}
          >
            <h3 className="text-xl mb-3 font-bold text-white">Feedback</h3>
            <div className="space-y-3 min-h-[120px]">
              {data.feedback.map((feedback, index) => (
                <motion.div 
                  key={index} 
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ 
                    opacity: activeFeedbackIndex >= index ? 1 : 0, 
                    x: activeFeedbackIndex >= index ? 0 : -20,
                    scale: activeFeedbackIndex === index ? 1.05 : 1
                  }}
                  transition={{ 
                    duration: 0.5,
                    ease: "easeOut"
                  }}
                  className={`flex items-start ${activeFeedbackIndex === index ? 'text-white font-medium' : 'text-gray-100'}`}
                >
                  <div className={`flex-shrink-0 w-6 h-6 mr-3 flex items-center justify-center rounded-sm transform ${
                    index % 4 === 0 ? 'bg-blue-900 text-blue-300 rotate-12' : 
                    index % 4 === 1 ? 'bg-green-900 text-green-300 -rotate-12' : 
                    index % 4 === 2 ? 'bg-purple-900 text-purple-300 rotate-12' :
                    'bg-yellow-900 text-yellow-300 -rotate-6'
                  }`}>
                    {index % 4 === 0 ? (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    ) : index % 4 === 1 ? (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" />
                      </svg>
                    ) : index % 4 === 2 ? (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
                      </svg>
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
                      </svg>
                    )}
                  </div>
                  <p className="text-base font-medium">{feedback}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Overall Section */}
        {(feedbackAnimationStarted || scoreAnimationStarted) && (
          <motion.div 
            className="mt-2 mb-4 text-center p-4 bg-[#232736] rounded-lg shadow-inner w-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: scoreAnimationStarted ? 1 : 0 }}
            transition={{ duration: 0.6 }}
          >
            <h3 className="text-lg font-semibold mb-2 text-left">Overall</h3>
            
            <div className="relative h-20 flex items-center justify-center">
              <motion.div 
                className="text-8xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500"
                initial="hidden"
                animate={scoreAnimationStarted ? ["initial", "final"] : "hidden"}
                variants={scoreVariants}
              >
                {data.complete_score}
              </motion.div>
            </div>
            
            {/* Overall Message with clearer styling */}
            {data.overall_message && (
              <motion.div 
                className="text-lg text-white max-w-lg mx-auto mt-4 p-3 bg-[#3A3F52] rounded-lg border border-indigo-400"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: messageAnimationStarted ? 1 : 0, y: messageAnimationStarted ? 0 : 20 }}
                transition={{ duration: 0.7, ease: "easeOut" }}
              >
                {data.overall_message || "Great job on this conversation! You demonstrated excellent skills."}
              </motion.div>
            )}
          </motion.div>
        )}

        <div className="mt-3 text-center">
          <motion.button
            onClick={onClose}
            className="px-5 py-1.5 bg-white text-black rounded-md font-medium transition-transform hover:scale-105"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            End Call
          </motion.button>
        </div>
      </div>
    </div>
  );
} 