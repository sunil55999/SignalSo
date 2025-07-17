import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function SettingsPanel() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>System Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Configure system settings and preferences.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}