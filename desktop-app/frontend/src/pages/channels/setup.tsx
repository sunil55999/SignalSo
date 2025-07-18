import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function ChannelSetup() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Channel Setup</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Telegram Channel Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Configure your Telegram channels for signal monitoring.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}