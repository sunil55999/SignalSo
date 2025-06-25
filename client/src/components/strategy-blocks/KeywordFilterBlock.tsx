import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  AlertTriangle, 
  Plus, 
  X, 
  HelpCircle,
  Filter,
  Check,
  XCircle
} from "lucide-react";
import { cn } from "@/lib/utils";

interface KeywordConfig {
  type: "required" | "blocked" | "conditional";
  keywords: string[];
  caseSensitive: boolean;
  exactMatch: boolean;
  action: "execute" | "block" | "modify";
}

interface KeywordFilterBlockProps {
  config: KeywordConfig;
  onChange: (config: KeywordConfig) => void;
}

export default function KeywordFilterBlock({ config, onChange }: KeywordFilterBlockProps) {
  const [newKeyword, setNewKeyword] = useState("");
  const [activeSection, setActiveSection] = useState<string>("required");

  const addKeyword = (keyword: string) => {
    if (keyword.trim() && !config.keywords.includes(keyword.trim())) {
      const updatedConfig = {
        ...config,
        keywords: [...config.keywords, keyword.trim()]
      };
      onChange(updatedConfig);
      setNewKeyword("");
    }
  };

  const removeKeyword = (keyword: string) => {
    const updatedConfig = {
      ...config,
      keywords: config.keywords.filter(k => k !== keyword)
    };
    onChange(updatedConfig);
  };

  const keywordSections = [
    {
      id: "required",
      name: "Required Keywords",
      description: "Signal must contain these words",
      color: "green",
      icon: Check,
      keywords: ["CLOSE FULLY", "CLOSE HALF"]
    },
    {
      id: "blocked", 
      name: "Blocked Keywords",
      description: "Signal will be blocked if contains these",
      color: "red",
      icon: XCircle,
      keywords: ["CLOSE", "keywords (optional)"]
    },
    {
      id: "conditional",
      name: "Conditional Keywords", 
      description: "Apply special rules when detected",
      color: "yellow",
      icon: AlertTriangle,
      keywords: []
    }
  ];

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <Filter className="w-5 h-5 text-blue-600" />
          <CardTitle>Keyword Filter Configuration</CardTitle>
          <HelpCircle className="w-4 h-4 text-muted-foreground" />
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Keyword Actions Notice */}
        <div className="bg-blue-50 dark:bg-blue-950/20 p-4 rounded-lg border border-blue-200">
          <div className="flex items-start space-x-2">
            <AlertTriangle className="w-5 h-5 text-blue-600 mt-0.5" />
            <div className="space-y-2">
              <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Keyword settings are not case-sensitive!
              </p>
              <div className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                <p><span className="font-medium text-green-600">Actions with the GREEN color</span> require the provider to reply to the signal message.</p>
                <p><span className="font-medium text-red-600">Actions with the RED color</span> don't require the provider to reply, but they must be included the point(s) in the action message.</p>
                <p><span className="font-medium text-purple-600">Actions with the PURPLE color</span> don't require the provider to reply, and will be executed on the last signal sent.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Keywords */}
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <Check className="w-5 h-5 text-green-600" />
            <Label className="font-medium">Update signal SL if the original message is edited</Label>
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
          </div>
          
          <div className="flex items-center space-x-2">
            <Check className="w-5 h-5 text-green-600" />
            <Label className="font-medium">Update signal TP's if the original message is edited</Label>
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
          </div>
          
          <div className="flex items-center space-x-2">
            <Check className="w-5 h-5 text-green-600" />
            <Label className="font-medium">Update signal ENTRYPOINT if the original message is edited</Label>
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
          </div>
          
          <div className="flex items-center space-x-2">
            <Check className="w-5 h-5 text-green-600" />
            <Label className="font-medium">Close the signal if the message is deleted</Label>
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
          </div>
        </div>

        {/* Warning Message */}
        <div className="bg-amber-50 dark:bg-amber-950/20 p-4 rounded-lg border border-amber-200">
          <div className="flex items-start space-x-2">
            <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
                Configure each word used by your provider to execute the following actions. The provider must reply to the signal message.
              </p>
            </div>
          </div>
        </div>

        {/* Keyword Configuration Sections */}
        {keywordSections.map((section) => {
          const Icon = section.icon;
          return (
            <div key={section.id} className="space-y-3">
              <div className="flex items-center space-x-2">
                <Icon className={cn(
                  "w-5 h-5",
                  section.color === "green" && "text-green-600",
                  section.color === "red" && "text-red-600", 
                  section.color === "yellow" && "text-yellow-600"
                )} />
                <Label className="font-medium text-sm">
                  {section.name}
                  <span className="text-xs text-muted-foreground ml-2">
                    ({section.description})
                  </span>
                </Label>
                <HelpCircle className="w-4 h-4 text-muted-foreground" />
              </div>
              
              <div className="flex items-center space-x-2">
                <Badge 
                  variant="outline" 
                  className={cn(
                    "text-xs px-2 py-1",
                    section.color === "green" && "border-green-500 text-green-700",
                    section.color === "red" && "border-red-500 text-red-700",
                    section.color === "yellow" && "border-yellow-500 text-yellow-700"
                  )}
                >
                  {section.id.toUpperCase()}
                </Badge>
                <span className="text-sm">the signal if the text</span>
                
                <div className="flex items-center space-x-1">
                  {section.keywords.map((keyword, index) => (
                    <Badge key={index} variant="secondary" className="text-xs">
                      {keyword}
                      <X 
                        className="w-3 h-3 ml-1 cursor-pointer hover:text-red-500" 
                        onClick={() => removeKeyword(keyword)}
                      />
                    </Badge>
                  ))}
                </div>
                
                <span className="text-sm">is detected, but not the text</span>
                <Input 
                  placeholder="keywords (optional)"
                  className="w-40 h-8 text-sm"
                />
                <HelpCircle className="w-4 h-4 text-muted-foreground" />
              </div>
            </div>
          );
        })}

        {/* Add Keyword Input */}
        <div className="flex items-center space-x-2 pt-4 border-t">
          <Input
            placeholder="Enter keyword..."
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && addKeyword(newKeyword)}
            className="flex-1"
          />
          <Select>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="required">Required</SelectItem>
              <SelectItem value="blocked">Blocked</SelectItem>
              <SelectItem value="conditional">Conditional</SelectItem>
            </SelectContent>
          </Select>
          <Button 
            size="sm" 
            onClick={() => addKeyword(newKeyword)}
            disabled={!newKeyword.trim()}
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        {/* Options */}
        <div className="space-y-3 pt-4 border-t">
          <div className="flex items-center justify-between">
            <Label htmlFor="case-sensitive" className="text-sm">
              Case sensitive matching
            </Label>
            <Switch
              id="case-sensitive"
              checked={config.caseSensitive}
              onCheckedChange={(checked) => 
                onChange({ ...config, caseSensitive: checked })
              }
            />
          </div>
          
          <div className="flex items-center justify-between">
            <Label htmlFor="exact-match" className="text-sm">
              Exact word matching only
            </Label>
            <Switch
              id="exact-match"
              checked={config.exactMatch}
              onCheckedChange={(checked) => 
                onChange({ ...config, exactMatch: checked })
              }
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}