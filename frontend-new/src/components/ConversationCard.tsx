import { Link } from "react-router-dom";
import { MessageSquare } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface ConversationCardProps {
  title: string;
  description: string;
  icon: string;
  messageCount?: string;
  to?: string;
}

const ConversationCard = ({ title, description, icon, messageCount, to = "/practice" }: ConversationCardProps) => {
  return (
    <Link to={to}>
      <Card className="group hover:border-primary/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 cursor-pointer h-full">
        <CardContent className="p-4 flex gap-4">
          <Avatar className="h-16 w-16 flex-shrink-0">
            <AvatarFallback className="text-2xl bg-primary/10 text-primary">
              {icon}
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-base mb-1 truncate group-hover:text-primary transition-colors">
              {title}
            </h3>
            <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
              {description}
            </p>
            {messageCount && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <MessageSquare className="h-3 w-3" />
                <span>{messageCount}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
};

export default ConversationCard;
