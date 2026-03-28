import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "AI Industry Value Estimator",
  description:
    "Bloomberg-style AI market research platform with econometric forecasts",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-bg text-text antialiased flex flex-col">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-8 flex-1 w-full">{children}</main>
        <footer className="border-t border-border mt-auto py-6 px-4">
          <p className="max-w-5xl mx-auto text-[10px] text-muted leading-relaxed">
            This platform provides estimated market sizing for informational and research purposes
            only. It does not constitute investment advice, financial guidance, or any recommendation
            to buy, sell, or hold securities. All projections are model-generated estimates subject
            to significant uncertainty. Past performance does not guarantee future results.
          </p>
        </footer>
      </body>
    </html>
  );
}
