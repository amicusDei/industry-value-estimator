import Link from "next/link";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/bubble-index", label: "Bubble Index" },
  { href: "/segments", label: "Segments" },
  { href: "/companies", label: "Companies" },
  { href: "/consensus", label: "Sources" },
  { href: "/diagnostics", label: "Diagnostics" },
  { href: "/methodology", label: "Methodology" },
];

export default function Navbar() {
  return (
    <nav className="border-b border-border bg-surface sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-8">
        <Link href="/" className="font-mono font-bold text-accent text-lg tracking-tight">
          AI-IVE
        </Link>
        <div className="flex gap-6">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm text-muted hover:text-text transition-colors"
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
