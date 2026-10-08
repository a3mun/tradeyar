"use client";

/**
 * GaugeChart — کیلومتر نیم‌دایره (نسخه ۲.۰)
 * ============================================================
 * 🔴 تغییرات:
 *   • گرادیانت نرم بین رنگ‌ها (شبیه TradingView)
 *   • تیک‌های عددی (0, 20, 40, 60, 80, 100)
 *   • عقربه‌ی پهن‌تر و واضح‌تر
 */

interface GaugeChartProps {
  value: number; // 0..100
  size?: number;
  colors?: string[]; // از راست به چپ (قرمز → سبز)
  showTicks?: boolean;
  showLabels?: boolean;
}

export function GaugeChart({
  value,
  size = 180,
  colors = ["#dc2626", "#ea580c", "#fbbf24", "#84cc16", "#16a34a"],
  showTicks = true,
  showLabels = true,
}: GaugeChartProps) {
  const clampedValue = Math.max(0, Math.min(100, value));

  // ─── ابعاد ───
  const cx = size / 2;
  const cy = size * 0.58;
  const radius = size * 0.42;
  const strokeWidth = size * 0.09;
  const tickLength = size * 0.04;

  // ─── نیم‌دایره: از ۱۸۰° (چپ = 0%) تا ۳۶۰° (راست = 100%) ───
  // ⚠️ در RTL، چپ = 0% (ترس)، راست = 100% (طمع)
  const startAngle = 180;
  const totalAngle = 180;

  const polarToCartesian = (
    cx: number,
    cy: number,
    r: number,
    angleDeg: number
  ) => {
    const angleRad = ((angleDeg - 90) * Math.PI) / 180;
    return {
      x: cx + r * Math.cos(angleRad),
      y: cy + r * Math.sin(angleRad),
    };
  };

  const arcPath = (startAngle: number, endAngle: number, r: number) => {
    const start = polarToCartesian(cx, cy, r, startAngle);
    const end = polarToCartesian(cx, cy, r, endAngle);
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
  };

  // ─── عقربه ───
  // 0% → 180°، 100% → 360°
  const needleAngle = startAngle + (clampedValue / 100) * totalAngle;
  const needleRad = ((needleAngle - 90) * Math.PI) / 180;
  const needleLength = radius * 0.85;
  const needleX = cx + needleLength * Math.cos(needleRad);
  const needleY = cy + needleLength * Math.sin(needleRad);

  // ─── تیک‌های عددی ───
  const ticks = [0, 20, 40, 60, 80, 100];

  return (
    <svg
      viewBox={`0 0 ${size} ${size * 0.72}`}
      className="mx-auto block"
      style={{ maxWidth: size }}
    >
      <defs>
        {/* گرادیانت نرم بین رنگ‌ها */}
        <linearGradient id={`gauge-grad-${size}`} x1="0%" y1="0%" x2="100%" y2="0%">
          {colors.map((c, i) => (
            <stop
              key={i}
              offset={`${(i / (colors.length - 1)) * 100}%`}
              stopColor={c}
            />
          ))}
        </linearGradient>
      </defs>

      {/* ═══ قوس رنگی (گرادیانت) ═══ */}
      <path
        d={arcPath(startAngle, startAngle + totalAngle, radius)}
        stroke={`url(#gauge-grad-${size})`}
        strokeWidth={strokeWidth}
        fill="none"
        strokeLinecap="round"
      />

      {/* ═══ تیک‌ها و برچسب‌ها ═══ */}
      {showTicks &&
        ticks.map((tick) => {
          const angle = startAngle + (tick / 100) * totalAngle;
          const rad = ((angle - 90) * Math.PI) / 180;
          const outerR = radius + strokeWidth / 2 + 2;
          const innerR = outerR - tickLength;

          const outer = polarToCartesian(cx, cy, outerR, angle);
          const inner = polarToCartesian(cx, cy, innerR, angle);
          const labelPos = polarToCartesian(cx, cy, outerR + size * 0.06, angle);

          return (
            <g key={tick}>
              <line
                x1={inner.x}
                y1={inner.y}
                x2={outer.x}
                y2={outer.y}
                stroke="currentColor"
                strokeWidth={1}
                className="text-muted-foreground/50"
              />
              {showLabels && (
                <text
                  x={labelPos.x}
                  y={labelPos.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={size * 0.05}
                  className="fill-muted-foreground"
                  style={{ fontFamily: "monospace" }}
                >
                  {tick}
                </text>
              )}
            </g>
          );
        })}

      {/* ═══ عقربه ═══ */}
      <line
        x1={cx}
        y1={cy}
        x2={needleX}
        y2={needleY}
        stroke="currentColor"
        strokeWidth={size * 0.018}
        strokeLinecap="round"
        className="text-foreground"
        style={{ transition: "all 0.6s cubic-bezier(0.4, 0, 0.2, 1)" }}
      />

      {/* ═══ دایره‌ی مرکز ═══ */}
      <circle cx={cx} cy={cy} r={size * 0.04} fill="currentColor" className="text-foreground" />
      <circle cx={cx} cy={cy} r={size * 0.02} fill="currentColor" className="fill-background" />
    </svg>
  );
}