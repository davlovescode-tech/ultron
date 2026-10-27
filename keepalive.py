"""Tiny web server so Render sees an open port and uptimebot.com has something to ping."""
import logging

from aiohttp import web

log = logging.getLogger("jarvis.keepalive")


async def start_keepalive(port: int):
    async def index(_request):
        return web.Response(text="J.A.R.V.I.S. online. All systems nominal.")

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/health", index)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("Keep-alive server listening on port %s", port)
    return runner
