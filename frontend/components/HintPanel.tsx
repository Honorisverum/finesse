import { HintData } from '@/utils/types';

type HintPanelProps = {
  hint: HintData | null;
};

export default function HintPanel({ hint }: HintPanelProps) {
  // Create a placeholder hint when no actual hint exists
  const placeholderHint: HintData = {
    hint: 'Waiting for hints from the AI assistant...',
    category: 'Loading'
  };

  // Use the real hint or the placeholder
  const displayHint = hint || placeholderHint;

  return (
    <div className="w-full bg-gray-800 rounded-lg shadow-lg overflow-hidden">
      <div className="p-4 space-y-3">
        {/* Category display */}
        <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">
          {displayHint.category}
        </div>
        
        {/* Hint with light bulb icon */}
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-1">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-white text-sm font-medium">{displayHint.hint}</p>
          </div>
        </div>
      </div>
    </div>
  );
} 