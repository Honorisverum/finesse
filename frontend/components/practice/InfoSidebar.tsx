"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Target, User, MessageSquare } from "lucide-react";
import { ScenarioData } from "@/types/database";

interface InfoSidebarProps {
  scenario: ScenarioData;
}

export default function InfoSidebar({ scenario }: InfoSidebarProps) {
  return (
    <aside className="w-96 border-l border-border bg-card p-6">
      <ScrollArea className="h-full">
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold mb-2">{scenario.title}</h2>
            <p className="text-sm text-muted-foreground">{scenario.description}</p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5 text-primary" />
                Your Goal
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">{scenario.goal}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5 text-primary" />
                Character
              </CardTitle>
              <CardDescription>{scenario.botname}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-2">
                {scenario.character.map((trait, index) => (
                  <li key={index} className="flex gap-2">
                    <span className="text-primary">•</span>
                    <span>{trait}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-primary" />
                Opening
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm italic">{scenario.opening}</p>
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </aside>
  );
}
