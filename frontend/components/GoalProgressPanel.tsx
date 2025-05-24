import React from 'react';
import { GoalProgressData } from '@/utils/types';

type GoalProgressPanelProps = {
  data: GoalProgressData | null;
};

export default function GoalProgressPanel({ data }: GoalProgressPanelProps) {
  if (!data) return null;

  // Calculate colors for progress bar (red to green gradient)
  const getProgressColor = (progress: number) => {
    // From red (0) to green (10)
    const red = Math.round(255 * (1 - progress / 10));
    const green = Math.round(255 * (progress / 10));
    return `rgb(${red}, ${green}, 0)`;
  };

  // Convert progress from 0-10 scale to percentage for positioning (0-100%)
  const progressPercentage = (data.progress_towards_goal / 10) * 100;

  return (
    <div className="w-full">
      {/* Main progress bar */}
      <div className="w-full bg-gray-900 rounded-lg shadow-lg p-4">
        {/* Progress labels */}
        <div className="flex justify-between items-center mb-1">
          <div className="text-sm text-red-400 font-medium">Not even close!</div>
          <div className="text-sm text-green-400 font-medium">You done it right!</div>
        </div>
        
        {/* Progress bar with notch */}
        <div className="relative w-full">
          {/* Gradient background */}
          <div className="w-full h-4 rounded-md overflow-hidden">
            <div className="w-full h-full" style={{ 
              background: 'linear-gradient(to right, rgb(220, 38, 38), rgb(34, 197, 94))'
            }}></div>
          </div>
          
          {/* Notch indicator */}
          <div 
            className="absolute top-0 w-3 h-6 bg-white shadow-md rounded-sm transition-all duration-300" 
            style={{ 
              left: `calc(${progressPercentage}% - 6px)`,
              transform: 'translateY(-1px)'
            }}
          ></div>
        </div>
      </div>
      
      {/* Status indicators (for debugging) */}
      <div className="flex gap-2 mt-2 opacity-70">
        <div className={`px-2 py-0.5 rounded-md text-xs font-medium ${
          data.is_goal_complete 
            ? "bg-green-800 text-green-100" 
            : "bg-gray-700 text-gray-300"
        }`}>
          Goal: {data.is_goal_complete ? "✓" : "✗"}
        </div>
        
        <div className={`px-2 py-0.5 rounded-md text-xs font-medium ${
          data.is_bad_ending_triggered 
            ? "bg-red-900 text-red-100" 
            : "bg-gray-700 text-gray-300"
        }`}>
          Bad: {data.is_bad_ending_triggered ? "✓" : "✗"}
        </div>
        
        {/* Debug value */}
        <div className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded-md text-xs font-medium">
          Value: {data.progress_towards_goal.toFixed(1)}/10
        </div>
      </div>
    </div>
  );
} 