import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";

import { AppToaster } from "@/components/app-toaster";
import "./globals.css";

// Swap these two imports (and their variable bindings) to change the app
// typography: --font-display feeds headings, --font-text feeds body copy.
const headingFont = Space_Grotesk({ subsets: ["latin"], variable: "--font-display" });
const bodyFont = Inter({ subsets: ["latin"], variable: "--font-text" });

export const metadata: Metadata = {
  title: "FIBA OCR Engine",
  description: "Invite-only FIBA scoresheet OCR demos and admin controls.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${headingFont.variable} ${bodyFont.variable} h-full antialiased`}>
      <body className="min-h-full">
        {children}
        <AppToaster />
      </body>
    </html>
  );
}
