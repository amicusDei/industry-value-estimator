"use client";

import { useState } from "react";
import { getExportUrl } from "@/lib/api";

interface Props {
  segment?: string;
  label?: string;
}

export default function ExportButton({ segment, label = "Export" }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="px-3 py-1.5 text-xs border border-border rounded text-muted hover:text-text hover:border-accent transition-colors"
      >
        {label} &#x25BE;
      </button>
      {open && (
        <div className="absolute right-0 mt-1 bg-surface border border-border rounded shadow-lg z-50 min-w-[120px]">
          <a
            href={getExportUrl("csv", segment)}
            className="block px-4 py-2 text-xs text-muted hover:text-text hover:bg-surface-hover"
            onClick={() => setOpen(false)}
          >
            Download CSV
          </a>
          <a
            href={getExportUrl("excel", segment)}
            className="block px-4 py-2 text-xs text-muted hover:text-text hover:bg-surface-hover"
            onClick={() => setOpen(false)}
          >
            Download Excel
          </a>
        </div>
      )}
    </div>
  );
}
