"use client";

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

// ═══ 🔴 Y-axis فقط بر اساس data (نه SL/TP) ═══
// چرا: اگه SL/TP توی range باشن، نوسانات واقعی قیمت
// ناچیز دیده میشن (خط صاف). پس فقط data رو در نظر بگیر،
// بعد با padding کوچیک نوسانات رو بزرگ‌تر نشون بده.
const dataMin = Math.min(...data);
const dataMax = Math.max(...data);
const dataRange = dataMax - dataMin || 1;

// ─── padding ۱۵٪ برای دیدن بهتر ───
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

  return (
    <div
      className={`relative overflow-hidden rounded-md bg-muted/10 ${className}`}
      style={{ height }}
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="block h-full w-full"
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
      </svg>
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