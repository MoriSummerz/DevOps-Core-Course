export interface Env {
  APP_NAME: string;
  COURSE_NAME: string;
  ENVIRONMENT: string;
  API_TOKEN: string;
  ADMIN_EMAIL: string;
  SETTINGS: KVNamespace;
}

const VERSION = "1.1.1";

function maskEmail(email: string | undefined): string {
  if (!email) return "";
  const [user, domain] = email.split("@");
  if (!domain) return "***";
  const visible = user.slice(0, 1);
  return `${visible}${"*".repeat(Math.max(user.length - 1, 1))}@${domain}`;
}

function tokenPresence(token: string | undefined): string {
  if (!token) return "missing";
  return `present (length=${token.length})`;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const colo = request.cf?.colo ?? "unknown";

    console.log("request", JSON.stringify({
      path,
      method: request.method,
      colo,
      country: request.cf?.country,
      ua: request.headers.get("user-agent"),
    }));

    if (path === "/health") {
      return Response.json({
        status: "ok",
        app: env.APP_NAME,
        version: VERSION,
        timestamp: new Date().toISOString(),
      });
    }

    if (path === "/") {
      return Response.json({
        app: env.APP_NAME,
        course: env.COURSE_NAME,
        environment: env.ENVIRONMENT,
        version: VERSION,
        message: "Hello from Cloudflare Workers — Lab 17 edge-api",
        endpoints: ["/", "/health", "/edge", "/counter", "/config"],
        timestamp: new Date().toISOString(),
      });
    }

    if (path === "/edge") {
      return Response.json({
        colo: request.cf?.colo,
        country: request.cf?.country,
        city: request.cf?.city,
        region: request.cf?.region,
        asn: request.cf?.asn,
        asOrganization: request.cf?.asOrganization,
        httpProtocol: request.cf?.httpProtocol,
        tlsVersion: request.cf?.tlsVersion,
        clientTcpRtt: request.cf?.clientTcpRtt,
        timezone: request.cf?.timezone,
        timestamp: new Date().toISOString(),
      });
    }

    if (path === "/counter") {
      const raw = await env.SETTINGS.get("visits");
      const visits = Number(raw ?? "0") + 1;
      await env.SETTINGS.put("visits", String(visits));
      return Response.json({
        visits,
        key: "visits",
        binding: "SETTINGS",
        timestamp: new Date().toISOString(),
      });
    }

    if (path === "/config") {
      return Response.json({
        app: env.APP_NAME,
        course: env.COURSE_NAME,
        environment: env.ENVIRONMENT,
        version: VERSION,
        secrets: {
          API_TOKEN: tokenPresence(env.API_TOKEN),
          ADMIN_EMAIL: maskEmail(env.ADMIN_EMAIL),
        },
        kv_binding: "SETTINGS",
      });
    }

    return new Response(JSON.stringify({ error: "Not Found", path }), {
      status: 404,
      headers: { "content-type": "application/json" },
    });
  },
} satisfies ExportedHandler<Env>;
