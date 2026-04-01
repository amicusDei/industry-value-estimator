"use client";

const SCENARIOS = [
  {
    id: "conservative",
    label: "Conservative",
    description: "Floor growth rates",
  },
  {
    id: "base",
    label: "Base",
    description: "1.3\u00d7 consensus",
  },
  {
    id: "aggressive",
    label: "Aggressive",
    description: "1.8\u00d7 consensus",
  },
] as const;

export type ScenarioId = (typeof SCENARIOS)[number]["id"];

interface Props {
  selected: ScenarioId;
  onChange: (scenario: ScenarioId) => void;
}

export default function ScenarioSelector({ selected, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {SCENARIOS.map((s) => {
        const isActive = selected === s.id;
        return (
          <button
            key={s.id}
            onClick={() => onChange(s.id)}
            className={`group relative px-4 py-2 rounded-full text-sm font-medium transition-all duration-150 ${
              isActive
                ? "bg-accent text-[#0a0a0f]"
                : "bg-transparent border border-[#ffffff20] text-muted hover:border-accent/50 hover:text-text"
            }`}
          >
            <span className="font-mono text-xs tracking-wide uppercase">
              {s.label}
            </span>
            {/* Tooltip */}
            <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 whitespace-nowrap rounded bg-[#1a1a2e] px-3 py-1.5 text-xs text-muted opacity-0 group-hover:opacity-100 transition-opacity border border-border shadow-lg">
              {s.description}
            </span>
          </button>
        );
      })}
    </div>
  );
}
