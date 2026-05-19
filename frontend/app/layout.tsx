import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "AI Music Dashboard",
  description: "AI-powered music marketing dashboard. Manage your releases, schedule content, and chat with AI.",
};

export const viewport: Viewport = {
  themeColor: "#f7f5f2",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} bg-[#f7f5f2]`}>
      <body className="font-sans bg-[#f7f5f2] text-slate-800 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
