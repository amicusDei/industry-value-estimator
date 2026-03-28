"use client";

import { useState } from "react";

interface Props {
  onChange: (valuation: "nominal" | "real_2020") => void;
}

export default function ValuationToggle({ onChange }: Props) {
  const [active, setActive] = useState<"nominal" | "real_2020">("nominal");

  const toggle = (v: "nominal" | "real_2020") => {
    setActive(v);
    onChange(v);
  };

  return (
    <div className="inline-flex rounded border border-border text-xs">
      <button
        onClick={() => toggle("nominal")}
        className={`px-3 py-1 transition-colors ${
          active === "nominal"
            ? "bg-accent text-bg font-semibold"
            : "text-muted hover:text-text"
        }`}
      >
        Nominal
      </button>
      <button
        onClick={() => toggle("real_2020")}
        className={`px-3 py-1 transition-colors ${
          active === "real_2020"
            ? "bg-accent text-bg font-semibold"
            : "text-muted hover:text-text"
        }`}
      >
        Real 2020
      </button>
    </div>
  );
}
