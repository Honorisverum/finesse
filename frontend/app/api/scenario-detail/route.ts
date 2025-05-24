import fs from 'fs';
import path from 'path';
import { NextResponse } from 'next/server';

// Force dynamic rendering for this API route
export const dynamic = 'force-dynamic';

// Path to scenarios directory
const scenariosDir = path.join(process.cwd(), '..', 'scenarios');

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const skill = searchParams.get('skill');
    const id = searchParams.get('id');
    
    if (!skill || !id) {
      return NextResponse.json({ 
        error: 'Missing skill or scenario id parameters' 
      }, { status: 400 });
    }
    
    // Construct the file path
    const filePath = path.join(scenariosDir, `${skill}.json`);
    
    // Check if file exists
    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ 
        error: `Skill ${skill} not found` 
      }, { status: 404 });
    }
    
    // Read the file and parse JSON
    try {
      const fileContent = fs.readFileSync(filePath, 'utf-8');
      const jsonData = JSON.parse(fileContent);
      
      // Get the specific scenario
      if (!jsonData[id]) {
        return NextResponse.json({ 
          error: `Scenario ${id} not found in skill ${skill}` 
        }, { status: 404 });
      }
      
      return NextResponse.json(jsonData[id]);
    } catch (err) {
      console.error(`Error processing file ${skill}.json:`, err);
      return NextResponse.json({ 
        error: 'Failed to process scenario file' 
      }, { status: 500 });
    }
  } catch (error) {
    console.error('Error fetching scenario detail:', error);
    return NextResponse.json({ 
      error: 'Failed to fetch scenario detail' 
    }, { status: 500 });
  }
} 