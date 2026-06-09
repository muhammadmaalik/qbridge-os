"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Point = { step: number; energy: number };

export default function VqeEnergyChart({
  data,
  groundState,
}: {
  data: Point[];
  groundState?: number;
}) {
  const domain = useMemo((): [number, number] => {
    if (!data.length) return [-1.2, -0.8];
    const vals = data.map((d) => d.energy);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const span = max - min || 0.08;
    const pad = span * 0.12;
    return [min - pad, max + pad];
  }, [data]);

  if (!data.length) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-md border border-dashed border-gray-300 bg-gray-50">
        <p className="text-sm text-gray-500">No trajectory data yet.</p>
      </div>
    );
  }

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="step"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={{ stroke: "#d1d5db" }}
            label={{
              value: "Iteration",
              position: "insideBottom",
              offset: -4,
              fill: "#6b7280",
              fontSize: 11,
            }}
          />
          <YAxis
            domain={domain}
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={{ stroke: "#d1d5db" }}
            tickFormatter={(v) => Number(v).toFixed(4)}
            width={56}
          />
          <Tooltip
            contentStyle={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(value) => [`${Number(value).toFixed(6)} Ha`, "Energy"]}
            labelFormatter={(l) => `Iteration ${l}`}
          />
          {typeof groundState === "number" && (
            <ReferenceLine
              y={groundState}
              stroke="#2563eb"
              strokeDasharray="4 4"
              strokeOpacity={0.7}
            />
          )}
          <Line
            type="monotone"
            dataKey="energy"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: "#2563eb" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
