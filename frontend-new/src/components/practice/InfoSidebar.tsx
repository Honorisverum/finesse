import { Clock, MessageSquare, Target, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

interface InfoSidebarProps {
  scenario: string;
}

const InfoSidebar = ({ scenario }: InfoSidebarProps) => {
  return (
    <aside className="w-80 border-l border-border bg-card flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
              <User className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-lg mb-1">Practice Scenario</h3>
              <p className="text-sm text-muted-foreground">
                AI-generated persona
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="flex-1 p-6 space-y-6 overflow-auto">
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <Target className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div>
              <h4 className="text-sm font-medium mb-1">Scenario</h4>
              <p className="text-sm text-muted-foreground">{scenario}</p>
            </div>
          </div>

          <Separator />

          <div className="flex items-start gap-3">
            <MessageSquare className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div>
              <h4 className="text-sm font-medium mb-1">Type</h4>
              <p className="text-sm text-muted-foreground">Voice Practice</p>
            </div>
          </div>

          <Separator />

          <div className="flex items-start gap-3">
            <Clock className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div>
              <h4 className="text-sm font-medium mb-1">Created</h4>
              <p className="text-sm text-muted-foreground">Just now</p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-border space-y-2">
        <Button variant="outline" className="w-full justify-start" size="sm">
          <MessageSquare className="h-4 w-4 mr-2" />
          New Practice
        </Button>
        <Button variant="outline" className="w-full justify-start" size="sm">
          <Clock className="h-4 w-4 mr-2" />
          History
        </Button>
      </div>
    </aside>
  );
};

export default InfoSidebar;
