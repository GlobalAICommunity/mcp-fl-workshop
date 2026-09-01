"""Modern MCP approval flow using FastMCP 4 and protocol revision 2026-07-28.

The fictional hold is never booked and no network service is contacted. The
server returns InputRequiredResult, and FastMCP's auto-mode client reissues the
tool call after the user accepts, declines, or cancels the request.
"""

from __future__ import annotations

import asyncio

from fastmcp import Client, Context, FastMCP
from fastmcp.client.elicitation import ElicitResult as ClientElicitResult
from mcp.types import (
    ElicitRequest,
    ElicitRequestFormParams,
    ElicitResult,
    InputRequiredResult,
)

mcp = FastMCP("Fictional Flight Approval")


@mcp.tool
async def hold_flight(
    flight_number: str,
    passenger_name: str,
    ctx: Context,
) -> str | InputRequiredResult:
    """Request approval before placing a fictional, no-cost flight hold."""
    responses = ctx.input_responses
    if responses is None:
        return InputRequiredResult(
            input_requests={
                "approval": ElicitRequest(
                    params=ElicitRequestFormParams(
                        message=(
                            f"Approve a fictional hold on {flight_number} "
                            f"for {passenger_name}?"
                        ),
                        requested_schema={
                            "type": "object",
                            "properties": {
                                "approved": {
                                    "type": "boolean",
                                    "title": "Approve hold",
                                }
                            },
                            "required": ["approved"],
                        },
                    )
                )
            }
        )

    approval = responses["approval"]
    if not isinstance(approval, ElicitResult):
        return "Hold not placed: the client returned an invalid approval response."
    if approval.action == "decline":
        return "Hold declined. No action was taken."
    if approval.action == "cancel":
        return "Hold cancelled. No action was taken."
    if not approval.content or not approval.content.get("approved"):
        return "Hold declined. No action was taken."
    return f"Fictional hold placed for {passenger_name} on {flight_number}."


async def approval_handler(message, response_type, params, context):
    """Collect a non-sensitive approval choice from the terminal user."""
    print(message)
    choice = await asyncio.to_thread(input, "Choose [y]es, [n]o, or [c]ancel: ")
    normalized = choice.strip().lower()
    if normalized == "c":
        return ClientElicitResult(action="cancel")
    if normalized != "y":
        return ClientElicitResult(action="decline")
    return ClientElicitResult(action="accept", content={"approved": True})


async def main() -> None:
    async with Client(
        mcp,
        mode="auto",
        elicitation_handler=approval_handler,
        input_required_max_rounds=2,
    ) as client:
        result = await client.call_tool(
            "hold_flight",
            {"flight_number": "LAB 309", "passenger_name": "Asha"},
        )
        print(result.data)


if __name__ == "__main__":
    asyncio.run(main())