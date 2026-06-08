import React, { useEffect, useRef, useState } from "react";

interface ProgressCircleProps {
  progress: number; // 0 to 1
  size?: number;
  strokeWidth?: number;
  backgroundColor?: string;
  fillColor?: string;
  borderColor?: string;
}

const ProgressCircle: React.FC<ProgressCircleProps> = ({
  progress,
  size = 56,
  strokeWidth = 8,
  backgroundColor = "var(--colorNeutralBackground6)",
  fillColor = "var(--colorPaletteSeafoamBorderActive)",
  borderColor = "var(--colorNeutralStroke1)",
}) => {
  const circleRef = useRef<SVGCircleElement>(null);
  const [hasMounted, setHasMounted] = useState(false);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    const circle = circleRef.current;
    if (circle) {
      const offset = circumference * (1 - progress);

      if (hasMounted) {
        circle.style.transition = "stroke-dashoffset 0.6s ease";
      } else {
        circle.style.transition = "none";
        setHasMounted(true);
      }

      circle.style.strokeDashoffset = `${offset}`;
    }
  }, [progress, circumference, hasMounted]);

  return (
    <div
      style={{
        position: "relative",
        width: size,
        height: size,
      }}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={backgroundColor}
          strokeWidth={strokeWidth}
          style={{ stroke: backgroundColor, strokeWidth, strokeDasharray: "none", strokeDashoffset: 0, strokeLinecap: "round", filter: "none" }}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius+4}
          fill="none"
          stroke={borderColor}
          strokeWidth={1}
          style={{ pointerEvents: "none" }}
        />
        <circle
          ref={circleRef}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={fillColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius-4}
          fill="none"
          stroke={borderColor}
          strokeWidth={1}
          style={{ pointerEvents: "none" }}
        />
      </svg>

      {progress >= 1 && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            fontSize: size * 0.3,
            lineHeight: 1,
            textAlign: "center",
            paddingBottom:'2px'
          }}
        >
          🚀
        </div>
      )}
    </div>
  );
};

export default ProgressCircle;
