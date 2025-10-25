import fs from 'fs';
import path from 'path';
import { NextResponse } from 'next/server';

// Путь к папке сценариев
const scenariosDir = path.join(process.cwd(), '..', 'scenarios');

// Тип для скилла
export type Skill = {
  name: string;
  scenarios: Scenario[];
};

// Тип для сценария - включает все поля из JSON
export type Scenario = {
  id: string;
  name: string;
  description: string;
  goal: string;
  opening: string;
  character: string[];
  negprompt: string[];
  skill: string;
  botname: string;
  botgender: string;
  voice_description: string;
  elevenlabs_voice_id: string;
  [key: string]: any;  // Для дополнительных полей
};

// Не кэшировать результаты
export const revalidate = 0;

export async function GET() {
  try {
    // Проверяем существование директории
    if (!fs.existsSync(scenariosDir)) {
      return NextResponse.json({ 
        error: 'Scenarios directory not found' 
      }, { status: 404 });
    }
    
    // Получаем список JSON файлов
    const files = fs.readdirSync(scenariosDir).filter(file => file.endsWith('.json'));
    
    if (files.length === 0) {
      return NextResponse.json({ 
        error: 'No JSON files found in scenarios directory' 
      }, { status: 404 });
    }
    
    // Массив скиллов
    const skills: Skill[] = [];
    
    // Обрабатываем каждый файл
    for (const file of files) {
      const skillName = path.basename(file, '.json');
      const filePath = path.join(scenariosDir, file);
      
      try {
        // Читаем содержимое файла
        const fileContent = fs.readFileSync(filePath, 'utf-8');
        const jsonData = JSON.parse(fileContent);
        
        // Создаем объект скилла
        const skill: Skill = {
          name: skillName,
          scenarios: []
        };
        
        // Добавляем сценарии из файла
        for (const [scenarioId, scenarioData] of Object.entries(jsonData)) {
          if (typeof scenarioData === 'object' && scenarioData !== null) {
            // Возвращаем ВСЕ поля сценария
            const scenario: any = {
              id: scenarioId,
              name: scenarioId,
              ...(scenarioData as any)  // Добавляем все поля из JSON
            };
            
            skill.scenarios.push(scenario);
          }
        }
        
        // Добавляем скилл в массив только если есть сценарии
        if (skill.scenarios.length > 0) {
          skills.push(skill);
        }
      } catch (err) {
        console.error(`Error processing file ${file}:`, err);
      }
    }
    
    // Если не нашли скиллов, возвращаем ошибку
    if (skills.length === 0) {
      return NextResponse.json({ 
        error: 'No valid skills or scenarios found in JSON files' 
      }, { status: 404 });
    }
    
    return NextResponse.json({ skills });
  } catch (error) {
    console.error('Error loading scenarios:', error);
    return NextResponse.json({ 
      error: 'Failed to load scenarios' 
    }, { status: 500 });
  }
} 