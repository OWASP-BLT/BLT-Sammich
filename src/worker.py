from pathlib import Path

from workers import Response


async def on_fetch(request, env):
    """Handle incoming HTTP requests and serve the HTML homepage."""
    html = Path(__file__).parent.joinpath("index.html").read_text(encoding="utf-8")
    return Response(html, headers={"Content-Type": "text/html; charset=utf-8"})
