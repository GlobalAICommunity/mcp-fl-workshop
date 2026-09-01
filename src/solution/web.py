"""Module 5 - the FastMCP 4 and Foundry Local agent loop in a browser.

Start it:

    .venv/Scripts/python -m uvicorn --app-dir src/solution web:app --port 7932

then open http://127.0.0.1:7932
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_raw import run  # noqa: E402

LOGGER = logging.getLogger(__name__)
MAX_QUESTION_LENGTH = 1000

HTML = """<!doctype html>
<html lang="en-IN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:,">
    <title>Bharat MCP Travel Desk</title>
    <style>
        :root { color-scheme: light; --ink: #111820; --paper: #f7f8f4; --line: #c8cfd1; --saffron: #d96824; --green: #17613d; --navy: #193a63; }
        * { box-sizing: border-box; }
        body { margin: 0; min-height: 100vh; color: var(--ink); background: var(--paper); font-family: 'Palatino Linotype', Georgia, serif; }
        header { display: flex; align-items: baseline; justify-content: space-between; gap: 24px; padding: 22px clamp(20px, 5vw, 72px); color: white; background: var(--navy); border-bottom: 5px solid var(--saffron); }
        h1 { margin: 0; font-size: clamp(24px, 4vw, 42px); font-weight: 600; letter-spacing: 0; }
        header span { color: #d8efe2; font-family: ui-monospace, monospace; font-size: 12px; text-transform: uppercase; }
        main { width: min(920px, 100%); margin: 0 auto; padding: 28px clamp(16px, 4vw, 40px) 40px; }
        #thread { min-height: 54vh; display: flex; flex-direction: column; gap: 18px; padding-bottom: 28px; }
        .message { max-width: 78%; padding: 14px 0; border-bottom: 1px solid var(--line); line-height: 1.55; white-space: pre-wrap; }
        .user { align-self: flex-end; color: var(--green); }
        .assistant { align-self: flex-start; }
        .label { display: block; margin-bottom: 7px; color: #6a675e; font-family: ui-monospace, monospace; font-size: 11px; text-transform: uppercase; }
        .tools { margin: 8px 0 0; color: var(--saffron); font-family: ui-monospace, monospace; font-size: 12px; }
        form { position: sticky; bottom: 0; display: grid; grid-template-columns: 1fr auto; gap: 10px; padding: 14px 0; background: var(--paper); border-top: 2px solid var(--ink); }
        input { min-width: 0; padding: 13px 4px; border: 0; border-bottom: 1px solid var(--line); outline: none; background: transparent; color: var(--ink); font: 17px Georgia, serif; }
        input:focus { border-color: var(--green); }
        button { min-height: 46px; padding: 0 22px; border: 0; border-radius: 4px; background: var(--green); color: white; font: 600 14px ui-monospace, monospace; cursor: pointer; }
        button:disabled { opacity: .55; cursor: wait; }
        @media (max-width: 560px) { header { align-items: flex-start; flex-direction: column; gap: 6px; } .message { max-width: 92%; } button { padding: 0 14px; } }
    </style>
</head>
<body>
    <header><h1>Bharat Travel Desk</h1><span>FastMCP 4 + Foundry Local</span></header>
    <main>
        <section id="thread" aria-live="polite"></section>
        <form id="chat"><input id="question" autocomplete="off" maxlength="1000" aria-label="Travel question" placeholder="Ask about Pune weather or a flight to Kochi" required><button>Send</button></form>
    </main>
    <script>
        const form = document.querySelector('#chat');
        const input = document.querySelector('#question');
        const thread = document.querySelector('#thread');
        function addMessage(kind, text, tools = []) {
            const message = document.createElement('article');
            message.className = `message ${kind}`;
            const label = document.createElement('span');
            label.className = 'label'; label.textContent = kind === 'user' ? 'You' : 'Travel desk';
            const body = document.createElement('div'); body.textContent = text;
            message.append(label, body);
            if (tools.length) {
                const calls = document.createElement('div'); calls.className = 'tools';
                calls.textContent = tools.map(tool => `${tool.name}(${JSON.stringify(tool.arguments)})`).join('  /  ');
                message.append(calls);
            }
            thread.append(message); message.scrollIntoView({ behavior: 'smooth' });
        }
        form.addEventListener('submit', async event => {
            event.preventDefault(); const question = input.value.trim(); if (!question) return;
            addMessage('user', question); input.value = ''; form.querySelector('button').disabled = true;
            try {
                const response = await fetch('/api/chat', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ question }) });
                const data = await response.json();
                addMessage('assistant', data.answer || data.error, data.tools || []);
            } catch (error) { addMessage('assistant', `Request failed: ${error.message}`); }
            finally { form.querySelector('button').disabled = false; input.focus(); }
        });
    </script>
</body>
</html>"""


async def homepage(request: Request) -> HTMLResponse:
    return HTMLResponse(HTML)


async def chat(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
        question = (
            str(payload.get("question", "")).strip()
            if isinstance(payload, dict)
            else ""
        )
    except (TypeError, ValueError):
        question = ""
    if not question:
        return JSONResponse({"error": "Question is required."}, status_code=400)
    if len(question) > MAX_QUESTION_LENGTH:
        return JSONResponse(
            {"error": f"Question must be {MAX_QUESTION_LENGTH} characters or fewer."},
            status_code=400,
        )

    tools: list[dict] = []
    try:
        answer = await run(
            question,
            on_tool_call=lambda name, arguments: tools.append(
                {"name": name, "arguments": arguments}
            ),
        )
    except Exception:  # noqa: BLE001
        LOGGER.exception("Local chat request failed")
        return JSONResponse(
            {"error": "Local request failed. Check the terminal for details."},
            status_code=500,
        )
    return JSONResponse({"answer": answer, "tools": tools})


app = Starlette(routes=[Route("/", homepage), Route("/api/chat", chat, methods=["POST"])])
