import { redirect } from "next/navigation";

import { destinationForAccount, getCurrentUserAccount } from "@/lib/auth/account";

export default async function Home() {
  const current = await getCurrentUserAccount();
  redirect(current ? destinationForAccount(current.account) : "/login");
}
