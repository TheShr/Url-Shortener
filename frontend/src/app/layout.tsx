import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShortURL — Fast Link Shortener",
  description: "Create short, trackable links in seconds. Includes real-time click analytics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {/* Background canvas */}
        <div className="bg-canvas" aria-hidden>
          <div className="grid" />
          <div className="blob-1" />
          <div className="blob-2" />
          <div className="blob-3" />
        </div>
        {children}
      </body>
    </html>
  );
}
