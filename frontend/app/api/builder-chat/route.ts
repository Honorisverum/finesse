import { generateObject } from 'ai';
import { openai } from '@ai-sdk/openai';
import { z } from 'zod';

export async function POST(req: Request) {
  try {
    const { prompt }: { prompt: string } = await req.json();

    if (!prompt) {
      return Response.json(
        { error: 'Prompt is required' },
        { status: 400 }
      );
    }

    const result = await generateObject({
      model: openai('gpt-4o-mini'),
      system: 'You are a helpful assistant that generates structured roleplay scenarios for communication practice.',
      prompt,
      schema: z.object({
        context: z.string().describe('A description of the communication scenario and situation'),
        persona: z.object({
          name: z.string().describe('Name of the person to practice with'),
          role: z.string().describe('Their role or title'),
          traits: z.string().describe('Key personality traits')
        }).describe('The character/person the user will be practicing communication with'),
        objections: z.array(z.string()).describe('List of potential questions or objections that might come up in this conversation')
      }),
    });

    console.log('Generated result:', JSON.stringify(result, null, 2));

    // Return just the object directly instead of using toJsonResponse
    return Response.json(result.object);

  } catch (error) {
    console.error('Error in builder-chat API:', error);
    return Response.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
