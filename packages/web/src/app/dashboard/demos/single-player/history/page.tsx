import type { Metadata } from "next";

import { HistoryClient } from "@/components/single-player-demo/history-client";

export const metadata: Metadata = {
  title: "History · Single Player Improve · FIBA OCR",
  description: "Review the games you have saved and revisit any past performance.",
};

export default function HistoryPage() {
  return <HistoryClient />;
}
