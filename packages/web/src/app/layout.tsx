import type { Metadata } from "next";

import { AppToaster } from "@/components/app-toaster";
import "./globals.css";

export const metadata: Metadata = {
  title: "FIBA OCR Engine",
  description: "Beta dashboard for FIBA scoresheet OCR API keys and quickstart docs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        {children}
        <AppToaster />
      </body>
    </html>
  );
}
