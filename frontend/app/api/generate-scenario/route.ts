import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import { GenerateScenarioRequest, GenerateScenarioResponse } from "@/types/database";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    const body: GenerateScenarioRequest = await request.json();
    const { scenario, goal } = body;

    if (!scenario || !goal) {
      return NextResponse.json(
        { error: "Missing scenario or goal" },
        { status: 400 }
      );
    }

    // Generate scenario using OpenAI
    const completion = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content: `You are a scenario generator for conversation practice. Generate a realistic character and scenario based on the user's description.

Return a JSON object with these fields:
- botname: The character's name
- botgender: "male", "female", or "neutral"
- goal: The user's objective (use the provided goal)
- opening: Initial message from the character (can include roleplay in *asterisks*)
- character: Array of 3-5 strings describing personality, background, communication style
- negprompt: Array of 3-5 strings describing how the character resists or challenges the user
- voice_description: Description of voice characteristics for text-to-speech

Be creative and realistic. Make the character challenging but fair.`
        },
        {
          role: "user",
          content: `Scenario: ${scenario}\nGoal: ${goal}`
        }
      ],
      temperature: 0.8,
      response_format: { type: "json_object" }
    });

    const generatedContent = completion.choices[0].message.content;
    if (!generatedContent) {
      throw new Error("No content generated");
    }

    const generated = JSON.parse(generatedContent);

    // Build complete scenario data
    const scenarioData: GenerateScenarioResponse["scenarioData"] = {
      id: `generated_${Date.now()}`,
      title: scenario,
      description: scenario,
      goal: goal,
      opening: generated.opening || "*The scenario begins* Hello.",
      character: generated.character || ["Professional character"],
      negprompt: generated.negprompt || ["Maintain professional distance"],
      skill: "custom",
      botname: generated.botname || "Practice Partner",
      botgender: generated.botgender || "neutral",
      voice_description: generated.voice_description || "Clear professional voice",
      elevenlabs_voice_id: "21m00Tcm4TlvDq8ikWAM" // Default ElevenLabs voice
    };

    return NextResponse.json({ scenarioData } as GenerateScenarioResponse);

  } catch (error) {
    console.error("Error generating scenario:", error);
    return NextResponse.json(
      { error: "Failed to generate scenario" },
      { status: 500 }
    );
  }
}

export const runtime = 'nodejs';
