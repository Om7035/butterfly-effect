import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "butterfly-effect — Causal Chain Tracer",
  description:
    "Run an event. Run the counterfactual. Subtract. See the true causal chain.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0a0e1a] text-gray-100 antialiased">{children}</body>
    </html>
  );
}
