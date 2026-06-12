import type { Metadata } from "next";

import { CaptureClient } from "@/components/single-player-demo/capture-client";

export const metadata: Metadata = {
  title: "Capture Game · Single Player Improve · FIBA OCR",
  description: "Upload a FIBA scoresheet and see your points and fouls in seconds.",
};

export default function CaptureGamePage() {
  return <CaptureClient />;
}
