"use client";

import { useEffect, useRef, useState } from "react";
import { getExportUrl } from "@/lib/api";

interface Props {
  segment?: string;
  scenario?: string;
  label?: string;
}

export default function ExportButton({
  segment,
  scenario = "base",
  label = "Export",
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div className="relative inline-block" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="px-3 py-1.5 text-xs border border-border rounded text-muted hover:text-text hover:border-accent transition-colors"
      >
        {label} &#x25BE;
      </button>
      {open && (
        <div className="absolute right-0 mt-1 bg-surface border border-border rounded shadow-lg z-50 min-w-[150px]">
          <a
            href={getExportUrl("excel", segment, scenario)}
            className="block px-4 py-2 text-xs text-muted hover:text-text hover:bg-surface-hover"
            onClick={() => setOpen(false)}
          >
            Excel (.xlsx)
          </a>
          <a
            href={getExportUrl("csv", segment, scenario)}
            className="block px-4 py-2 text-xs text-muted hover:text-text hover:bg-surface-hover"
            onClick={() => setOpen(false)}
          >
            CSV (.csv)
          </a>
        </div>
      )}
    </div>
  );
}
