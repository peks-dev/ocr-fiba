type HeaderReader = {
  get(name: string): string | null;
};

type OriginEnv = Record<string, string | undefined>;

const SAFE_HOST_RE = /^[a-z0-9.-]+(?::\d+)?$/i;

export function resolveAppOrigin(
  requestHeaders: HeaderReader,
  env: OriginEnv = process.env,
): string {
  const configured = parseHttpOrigin(env.NEXT_PUBLIC_SITE_URL) || parseHttpOrigin(env.SITE_URL);
  if (configured) return configured;

  const forwardedHost = firstHeaderValue(requestHeaders.get("x-forwarded-host"));
  const directHost = firstHeaderValue(requestHeaders.get("host"));
  const resolvedHost = cleanHost(forwardedHost || directHost);

  const originHeader = parseHttpOrigin(requestHeaders.get("origin"));
  if (originHeader && resolvedHost && new URL(originHeader).host === resolvedHost) {
    return originHeader;
  }

  if (resolvedHost) {
    const forwardedProto = firstHeaderValue(requestHeaders.get("x-forwarded-proto"));
    const proto =
      forwardedProto === "http" || forwardedProto === "https"
        ? forwardedProto
        : isLocalHost(resolvedHost)
          ? "http"
          : "https";
    return `${proto}://${resolvedHost}`;
  }

  const vercelHost =
    parseHttpOrigin(withHttpsScheme(env.VERCEL_PROJECT_PRODUCTION_URL)) ||
    parseHttpOrigin(withHttpsScheme(env.VERCEL_URL));
  if (vercelHost) return vercelHost;

  return "http://localhost:3000";
}

function firstHeaderValue(value: string | null): string | null {
  if (!value) return null;
  const first = value.split(",")[0]?.trim();
  return first || null;
}

function cleanHost(host: string | null): string | null {
  if (!host || !SAFE_HOST_RE.test(host)) return null;
  return host;
}

function isLocalHost(host: string): boolean {
  const hostname = host.split(":")[0]?.toLowerCase() || "";
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]";
}

function withHttpsScheme(hostOrUrl: string | undefined): string | undefined {
  const raw = hostOrUrl?.trim();
  if (!raw) return undefined;
  return /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
}

function parseHttpOrigin(value: string | undefined | null): string | null {
  const raw = value?.trim();
  if (!raw) return null;
  try {
    const url = new URL(raw);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.origin;
  } catch {
    return null;
  }
}
