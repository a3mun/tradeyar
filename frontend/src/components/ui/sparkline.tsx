"use client";

import { useState, useRef, useCallback } from "react";

interface SparklineProps {
  data: number[];
  height?: number;
  showArea?: boolean;
  showDot?: boolean;
  sl?: number | null;
  tp?: number | null;
  entry?: number | null;
  color?: "green" | "red" | "neutral" | "auto";
  className?: string;
}

export function Sparkline({
  data,
  height = 70,
  showArea = true,
  showDot = true,
  sl,
  tp,
  entry,
  color = "auto",
  className = "",
}: SparklineProps) {
  // 🔴 hover state
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  if (!data || data.length < 2) {
    return (
      <div
        className={`flex items-center justify-center rounded-md bg-muted/10 text-[9px] text-muted-foreground ${className}`}
        style={{ height }}
      >
        نمودار در دسترس نیست
      </div>
    );
  }

  const W = 300;
  const H = height;
  const PAD = 3;

  const dataMin = Math.min(...data);
  const dataMax = Math.max(...data);
  const dataRange = dataMax - dataMin || 1;

  const padding = dataRange * 0.15;
  const min = dataMin - padding;
  const max = dataMax + padding;
  const range = max - min || 1;

  const toY = (v: number) =>
    PAD + (1 - (v - min) / range) * (H - 2 * PAD);

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = toY(v);
    return [x, y] as const;
  });

  const linePath =
    "M " + points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" L ");

  const areaPath =
    showArea && points.length > 0
      ? linePath + ` L ${W},${H} L 0,${H} Z`
      : "";

  const trend = data[data.length - 1] >= data[0] ? "up" : "down";
  const autoColor = trend === "up" ? "#22c55e" : "#ef4444";

  const COLOR_MAP: Record<string, string> = {
    green: "#22c55e",
    red: "#ef4444",
    neutral: "#64748b",
    auto: autoColor,
  };

  const lineColor = COLOR_MAP[color] || autoColor;

  const gradientId = `spark-grad-${Math.random().toString(36).slice(2, 9)}`;

  // 🔴 محاسبه‌ی ایندکس بر اساس موقعیت موس
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const relX = (e.clientX - rect.left) / rect.width; // 0..1
      const idx = Math.round(relX * (data.length - 1));
      const clamped = Math.max(0, Math.min(data.length - 1, idx));
      setHoverIndex(clamped);
    },
    [data.length]
  );

  const handleMouseLeave = useCallback(() => {
    setHoverIndex(null);
  }, []);

  // 🔴 موقعیت tooltip (بر اساس hoverIndex)
  const hoverPoint = hoverIndex != null ? points[hoverIndex] : null;
  const hoverValue = hoverIndex != null ? data[hoverIndex] : null;
  const tooltipLeft = hoverPoint
    ? `${(hoverPoint[0] / W) * 100}%`
    : "0%";

  return (
    <div
      className={`relative overflow-hidden rounded-md bg-muted/10 ${className}`}
      style={{ height }}
    >
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="block h-full w-full cursor-crosshair"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={lineColor} stopOpacity="0.35" />
            <stop offset="100%" stopColor={lineColor} stopOpacity="0" />
          </linearGradient>
        </defs>

        {tp != null && tp > 0 && (
          <line
            x1="0"
            y1={toY(tp)}
            x2={W}
            y2={toY(tp)}
            stroke="#22c55e"
            strokeWidth="0.7"
            strokeDasharray="4,4"
            opacity="0.4"
          />
        )}

        {entry != null && entry > 0 && (
          <line
            x1="0"
            y1={toY(entry)}
            x2={W}
            y2={toY(entry)}
            stroke="#9ca3af"
            strokeWidth="0.7"
            strokeDasharray="2,3"
            opacity="0.35"
          />
        )}

        {sl != null && sl > 0 && (
          <line
            x1="0"
            y1={toY(sl)}
            x2={W}
            y2={toY(sl)}
            stroke="#ef4444"
            strokeWidth="0.7"
            strokeDasharray="4,4"
            opacity="0.4"
          />
        )}

        {showArea && areaPath && (
          <path d={areaPath} fill={`url(#${gradientId})`} />
        )}

        <path
          d={linePath}
          fill="none"
          stroke={lineColor}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {showDot && points.length > 0 && (
          <circle
            cx={points[points.length - 1][0]}
            cy={points[points.length - 1][1]}
            r="3"
            fill={lineColor}
          />
        )}

        {/* 🔴 خط عمودی + نقطه‌ی hover */}
        {hoverPoint && (
          <>
            <line
              x1={hoverPoint[0]}
              y1={0}
              x2={hoverPoint[0]}
              y2={H}
              stroke="#94a3b8"
              strokeWidth="1"
              strokeDasharray="2,2"
              opacity="0.6"
            />
            <circle
              cx={hoverPoint[0]}
              cy={hoverPoint[1]}
              r="4"
              fill={lineColor}
              stroke="#0a0e1a"
              strokeWidth="1.5"
            />
          </>
        )}
      </svg>

      {/* 🔴 tooltip (هوشمند: بالا یا پایین بر اساس موقعیت نقطه) */}
      {hoverValue != null && hoverPoint && (
        <div
          className={`pointer-events-none absolute z-10 -translate-x-1/2 rounded bg-slate-900/95 px-1.5 py-0.5 text-[10px] font-bold text-white shadow-lg ${
            hoverPoint[1] > H / 2 ? "-translate-y-[calc(100%+8px)]" : "translate-y-2"
          }`}
          style={{
            left: tooltipLeft,
            top: `${(hoverPoint[1] / H) * 100}%`,
          }}
        >
          {hoverValue.toLocaleString("en-US", {
            maximumFractionDigits: 2,
          })}
        </div>
      )}
    </div>
  );
}

interface MiniSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: "green" | "red" | "neutral" | "auto";
  className?: string;
}

export function MiniSparkline({
  data,
  height = 24,
  color = "auto",
  className = "",
}: MiniSparklineProps) {
  if (!data || data.length < 2) {
    return (
      <div
        className={`flex items-center justify-center rounded bg-muted/5 text-[8px] text-muted-foreground ${className}`}
        style={{ height }}
      >
        —
      </div>
    );
  }

  const W = 100;
  const H = height;
  const PAD = 2;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = PAD + (1 - (v - min) / range) * (H - 2 * PAD);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const path = "M " + points.join(" L ");

  const trend = data[data.length - 1] >= data[0] ? "up" : "down";
  const autoColor = trend === "up" ? "#22c55e" : "#ef4444";

  const COLOR_MAP: Record<string, string> = {
    green: "#22c55e",
    red: "#ef4444",
    neutral: "#64748b",
    auto: autoColor,
  };

  const lineColor = COLOR_MAP[color] || autoColor;

  return (
    <div
      className={`overflow-hidden rounded bg-muted/5 ${className}`}
      style={{ height }}
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="block h-full w-full"
      >
        <path
          d={path}
          fill="none"
          stroke={lineColor}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}