import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const OPENAI_API_KEY = process.env.FOPENAI_API_KEY;

export async function POST(request: Request) {
  try {
    const { userInput } = await request.json();

    if (!userInput) {
      return NextResponse.json({
        error: 'userInput is required'
      }, { status: 400 });
    }

    if (!OPENAI_API_KEY) {
      return NextResponse.json({
        error: 'FOPENAI_API_KEY not configured'
      }, { status: 500 });
    }

    // Call OpenAI to generate a smart follow-up question
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        temperature: 0.7,
        messages: [
          {
            role: 'system',
            content: `You are an expert communication coach helping users identify their specific needs.

Your task: Generate ONE insightful follow-up question based on what the user wants to practice.

Guidelines:
- Ask about specific situations, contexts, or challenges they face
- Make it relevant and concrete, not generic
- Keep it conversational and friendly
- The question should help clarify what scenarios would be most useful for them
- Aim for 1-2 sentences max

Examples:
User: "Dating"
Follow-up: "What stage are you working on - meeting new people, first dates, or building deeper connections?"

User: "Negotiation"
Follow-up: "Are you preparing for a specific negotiation, like a salary discussion or business deal, or working on general negotiation skills?"

User: "Conflict Resolution"
Follow-up: "What situations do you find most challenging - disagreements with colleagues, receiving criticism, or managing team conflicts?"

User: "Small Talk"
Follow-up: "Where do you most want to improve - starting conversations with strangers, keeping conversations going, or making them more engaging?"

Return ONLY the follow-up question text, nothing else.`
          },
          {
            role: 'user',
            content: userInput
          }
        ]
      })
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('OpenAI API error:', error);
      return NextResponse.json({
        error: 'Failed to generate follow-up question'
      }, { status: 500 });
    }

    const data = await response.json();
    const followUpQuestion = data.choices[0].message.content.trim();

    return NextResponse.json({
      question: followUpQuestion
    });

  } catch (error) {
    console.error('Error generating follow-up question:', error);
    return NextResponse.json({
      error: 'Internal server error'
    }, { status: 500 });
  }
}
