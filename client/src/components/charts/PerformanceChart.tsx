import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Area, AreaChart } from "recharts";
import { TrendingUp, Calendar, BarChart3 } from "lucide-react";
import { useState } from "react";

interface PerformanceData {
  date: string;
  pnl: number;
  cumulativePnl: number;
  trades: number;
  winRate: number;
}

export default function PerformanceChart() {
  const [timeframe, setTimeframe] = useState("7d");
  
  const { data: performanceData, isLoading } = useQuery({
    queryKey: ["/api/dashboard/performance", timeframe],
    refetchInterval: 30000,
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white/95 backdrop-blur-sm border border-slate-200 rounded-lg shadow-lg p-4">
          <p className="font-medium text-slate-900 mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center space-x-2 text-sm">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: entry.color }}
              ></div>
              <span className="text-slate-600">{entry.dataKey}:</span>
              <span className="font-medium text-slate-900">
                {entry.dataKey.includes('Pnl') || entry.dataKey.includes('pnl') 
                  ? `$${entry.value.toFixed(2)}`
                  : entry.dataKey === 'winRate'
                  ? `${entry.value.toFixed(1)}%`
                  : entry.value
                }
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <Card className="w-full shadow-lg border-0">
        <CardHeader>
          <div className="h-6 bg-slate-200 rounded animate-pulse"></div>
        </CardHeader>
        <CardContent>
          <div className="h-80 bg-slate-100 rounded animate-pulse"></div>
        </CardContent>
      </Card>
    );
  }

  const data: PerformanceData[] = performanceData || [
    { date: "Jan 20", pnl: 245, cumulativePnl: 1245, trades: 12, winRate: 75 },
    { date: "Jan 21", pnl: -180, cumulativePnl: 1065, trades: 8, winRate: 62.5 },
    { date: "Jan 22", pnl: 320, cumulativePnl: 1385, trades: 15, winRate: 80 },
    { date: "Jan 23", pnl: 180, cumulativePnl: 1565, trades: 10, winRate: 70 },
    { date: "Jan 24", pnl: -95, cumulativePnl: 1470, trades: 6, winRate: 66.7 },
    { date: "Jan 25", pnl: 425, cumulativePnl: 1895, trades: 18, winRate: 83.3 },
    { date: "Jan 26", pnl: 280, cumulativePnl: 2175, trades: 14, winRate: 78.6 }
  ];

  const timeframeOptions = [
    { value: "1d", label: "24H" },
    { value: "7d", label: "7D" },
    { value: "30d", label: "30D" },
    { value: "90d", label: "3M" }
  ];

  return (
    <Card className="w-full shadow-lg border-0">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-semibold flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-blue-600 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <span>Performance Chart</span>
          </CardTitle>
          
          <div className="flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-slate-500" />
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              {timeframeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <defs>
                <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.05}/>
                </linearGradient>
                <linearGradient id="cumulativeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05}/>
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis 
                dataKey="date" 
                stroke="#64748b"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                stroke="#64748b"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => `$${value}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ paddingTop: "20px" }}
                iconType="circle"
              />
              
              <Area
                type="monotone"
                dataKey="cumulativePnl"
                stroke="#3b82f6"
                strokeWidth={3}
                fill="url(#cumulativeGradient)"
                name="Cumulative P&L"
              />
              
              <Line
                type="monotone"
                dataKey="pnl"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ r: 4, fill: "#10b981" }}
                activeDot={{ r: 6, fill: "#10b981" }}
                name="Daily P&L"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-slate-200">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-1 mb-1">
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              <span className="text-sm font-medium text-slate-600">Total P&L</span>
            </div>
            <div className="text-xl font-bold text-emerald-600">
              +${data[data.length - 1]?.cumulativePnl.toLocaleString() || "0"}
            </div>
          </div>
          
          <div className="text-center">
            <div className="text-sm font-medium text-slate-600 mb-1">Avg Win Rate</div>
            <div className="text-xl font-bold text-blue-600">
              {(data.reduce((acc, d) => acc + d.winRate, 0) / data.length).toFixed(1)}%
            </div>
          </div>
          
          <div className="text-center">
            <div className="text-sm font-medium text-slate-600 mb-1">Total Trades</div>
            <div className="text-xl font-bold text-purple-600">
              {data.reduce((acc, d) => acc + d.trades, 0)}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}