import { Suspense } from "react";

import { InviteSetupCard } from "@/components/invite-setup-card";

export default function InvitePage() {
  return (
    <main className="grid min-h-screen place-items-center px-4 py-10 sm:px-6">
      <Suspense fallback={<div className="text-muted">Loading invitation...</div>}>
        <InviteSetupCard />
      </Suspense>
    </main>
  );
}
