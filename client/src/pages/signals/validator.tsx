import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function SignalValidator() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Signal Validator</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Signal Validation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Validate and test trading signals before execution.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}