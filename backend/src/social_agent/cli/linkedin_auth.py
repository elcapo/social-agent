from __future__ import annotations

import secrets
import urllib.parse

import click
import httpx

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_SCOPES = ["openid", "profile", "w_member_social"]


def _build_auth_url(client_id: str, state: str, redirect_uri: str) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(LINKEDIN_SCOPES),
        "state": state,
    }
    return f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def _exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


def _start_callback_server(state: str, port: int) -> str:
    import http.server
    import socket
    import threading

    code_received: list[str] = []
    event = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            if "code" in params and params.get("state", [""])[0] == state:
                code_received.append(params["code"][0])
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Autorizado</h1>"
                    b"<p>Ya puedes cerrar esta ventana y volver a la terminal.</p>"
                    b"</body></html>"
                )
                event.set()
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"<h1>Error: code or state mismatch</h1>")
                event.set()

        def log_message(self, format: str, *args: object) -> None:
            pass

    try:
        server = http.server.HTTPServer(("localhost", port), Handler)
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except OSError:
        raise OSError(
            f"El puerto {port} ya está en uso.\n"
            f"Usa --port para elegir otro puerto y configura "
            f"'http://localhost:<puerto>/callback' como redirect URI "
            f"en tu app de LinkedIn Developer Portal."
        )

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    event.wait(timeout=300)
    server.shutdown()

    if code_received:
        return code_received[0]
    raise TimeoutError("No se recibió el código de autorización en 300 segundos.")


def _save_to_env(token: str, env_path: str) -> None:
    lines: list[str] = []
    found = False
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith("SOCIAL_AGENT_LINKEDIN_ACCESS_TOKEN="):
                    lines.append(f"SOCIAL_AGENT_LINKEDIN_ACCESS_TOKEN={token}\n")
                    found = True
                else:
                    lines.append(line)
    except FileNotFoundError:
        pass

    if not found:
        lines.append(
            "\n# LinkedIn Access Token (generado por 'social-agent linkedin auth')\n"
        )
        lines.append(f"SOCIAL_AGENT_LINKEDIN_ACCESS_TOKEN={token}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

    click.echo(f"  Token guardado en {env_path}")


def _manual_code_input(redirect_uri: str) -> str:
    click.echo(
        "  Si el servidor automático no funciona, pega aquí la URL completa\n"
        "  a la que LinkedIn te redirigió después de autorizar:\n"
    )
    url = click.prompt("  URL de redirección", default="")
    if url:
        parsed = urllib.parse.urlparse(url.strip())
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            return params["code"][0]
    code = click.prompt("  O pega solo el código 'code' de la URL", default="")
    return code.strip()


async def auth_flow(
    client_id: str,
    client_secret: str,
    port: int = 8080,
    save: bool = False,
    env_file: str = ".env",
) -> str:
    redirect_uri = f"http://localhost:{port}/callback"
    state = secrets.token_urlsafe(16)
    auth_url = _build_auth_url(client_id, state, redirect_uri)

    click.echo("")
    click.echo("")
    click.echo("  ╔══════════════════════════════════════════════════════════╗")
    click.echo("  ║  Ve a tu app en LinkedIn Developer Portal y en Auth   ║")
    click.echo("  ║  → Authorized redirect URLs, asegúrate de que esté:   ║")
    click.echo("  ║                                                       ║")
    click.echo(f"  ║     {redirect_uri:<53}║")
    click.echo("  ║                                                       ║")
    click.echo("  ║  Luego abre esta URL en tu navegador y autoriza:      ║")
    click.echo("  ║                                                       ║")
    click.echo(f"  ║     {auth_url:<53}║")
    click.echo("  ╚══════════════════════════════════════════════════════════╝")
    click.echo("")

    code: str | None = None

    try:
        click.echo(f"  Iniciando servidor de callback en {redirect_uri} ...")
        code = _start_callback_server(state, port)
        click.echo("  Código de autorización recibido.\n")
    except (OSError, TimeoutError) as e:
        click.echo(f"  {e}\n")
        code = _manual_code_input(redirect_uri)

    if not code:
        click.echo("  No se proporcionó ningún código. Abortando.")
        return ""

    click.echo("  Intercambiando código por token de acceso...")
    token_data = await _exchange_code(client_id, client_secret, code, redirect_uri)
    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in")

    click.echo("  Token de acceso obtenido")
    if expires_in:
        click.echo(f"     Expira en: {expires_in} segundos ({expires_in // 86400} días)")

    if save:
        _save_to_env(access_token, env_file)
    else:
        click.echo(f"\n  SOCIAL_AGENT_LINKEDIN_ACCESS_TOKEN={access_token}\n")
        click.echo("  Copia esta línea en tu .env o ejecuta con --save")

    return access_token
