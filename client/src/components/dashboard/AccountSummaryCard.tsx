import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DollarSign, TrendingUp, TrendingDown, CreditCard, Shield } from 'lucide-react';
import { Account, License } from '@shared/schema';

interface AccountSummaryCardProps {
  account?: Account;
  license?: License;
  isLoading?: boolean;
}

export function AccountSummaryCard({ account, license, isLoading }: AccountSummaryCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Account Summary</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex justify-between items-center">
                <div className="h-4 bg-gray-200 rounded animate-pulse w-20"></div>
                <div className="h-4 bg-gray-200 rounded animate-pulse w-16"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: account?.currency || 'USD',
    }).format(amount);
  };

  const marginLevel = account?.marginLevel || 0;
  const marginColor = marginLevel > 300 ? 'text-green-600' : marginLevel > 150 ? 'text-yellow-600' : 'text-red-600';

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Account Summary</CardTitle>
        <DollarSign className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Primary Account Info */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Balance</span>
              <span className="text-sm font-medium">{formatCurrency(account?.balance || 0)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Equity</span>
              <span className="text-sm font-medium">{formatCurrency(account?.equity || 0)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Margin</span>
              <span className="text-sm font-medium">{formatCurrency(account?.margin || 0)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Open P&L</span>
              <span className={`text-sm font-medium flex items-center ${
                (account?.profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {(account?.profit || 0) >= 0 ? (
                  <TrendingUp className="h-3 w-3 mr-1" />
                ) : (
                  <TrendingDown className="h-3 w-3 mr-1" />
                )}
                {formatCurrency(account?.profit || 0)}
              </span>
            </div>
          </div>

          {/* Margin Level */}
          <div className="pt-2 border-t">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Margin Level</span>
              <span className={`text-sm font-medium ${marginColor}`}>
                {marginLevel.toFixed(2)}%
              </span>
            </div>
          </div>

          {/* License Status */}
          <div className="pt-2 border-t">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">License</span>
              <Badge 
                variant={license?.status === 'active' ? 'default' : 'destructive'}
                className="text-xs"
              >
                <Shield className="h-3 w-3 mr-1" />
                {license?.tier?.toUpperCase() || 'FREE'} - {license?.status || 'Unknown'}
              </Badge>
            </div>
          </div>

          {/* Account Details */}
          <div className="pt-2 border-t text-xs text-muted-foreground">
            <div className="flex justify-between">
              <span>Server</span>
              <span>{account?.server || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span>Leverage</span>
              <span>1:{account?.leverage || 'N/A'}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}