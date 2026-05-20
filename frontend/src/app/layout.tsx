import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KlusAI — Competitor Intelligence",
  description:
    "AI-powered competitor intelligence platform for recruitment agencies. Track competitor job postings, identify hiring companies, and generate prospect briefs.",
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
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
