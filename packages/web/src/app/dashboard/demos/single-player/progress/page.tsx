import type { Metadata } from "next";

import { ProgressClient } from "@/components/single-player-demo/progress-client";

export const metadata: Metadata = {
  title: "Progress · Single Player Improve · FIBA OCR",
  description: "Track your scoring and foul averages across your saved games.",
};

export default function ProgressPage() {
  return <ProgressClient />;
}
