"use client";

import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";

interface MiniChartProps {
  points: number[];
  positive: boolean;
}

/**
 * Small sparkline used on stock cards. Deliberately minimal -- no axes,
 * gridlines, or tooltips -- so it reads as a glance-able trend, not a
 * full chart (that's reserved for the Stock Detail page).
 */
export default function MiniChart({ points, positive }: MiniChartProps) {
  if (!points || points.length < 2) {
    return <div className="h-10 w-full" />;
  }

  const data = points.map((v, i) => ({ i, v }));
  const color = positive ? "#00875A" : "#D64545";

  return (
    <div className="h-10 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
