import { NextResponse } from "next/server";

import { destinationForAccount, markCurrentAccountAccepted } from "@/lib/auth/account";
import { createClient } from "@/lib/supabase/server";

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Not authenticated." }, { status: 401 });
  }

  const account = await markCurrentAccountAccepted(user.id);
  if (!account) {
    return NextResponse.json({ error: "Account not provisioned." }, { status: 404 });
  }

  return NextResponse.json({ destination: destinationForAccount(account) });
}
