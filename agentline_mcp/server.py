"""Agentline MCP server — exposes the Agentline SDK as MCP tools.

Transport: stdio (standard for Claude Desktop, Cursor, Zed, Windsurf, Continue).

Config:
  AGENTLINE_API_KEY  required, starts with ag_live_ or ag_test_
  AGENTLINE_BASE_URL optional, defaults to https://api.agentline.dev

Run:
  agentline-mcp              # installed script
  python -m agentline_mcp    # equivalent
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from typing import Any

from mcp.server.fastmcp import FastMCP

from agentline import Agentline, AgentlineError


DEFAULT_WAIT_TIMEOUT = 60.0
MAX_WAIT_TIMEOUT = 180.0


def _build_client() -> Agentline:
    api_key = os.environ.get("AGENTLINE_API_KEY", "").strip()
    if not api_key:
        print(
            "AGENTLINE_API_KEY is not set. Get a key at https://www.agentline.co "
            "and export it before running this server.",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = os.environ.get("AGENTLINE_BASE_URL", "").strip() or None
    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return Agentline(**kwargs)


mcp = FastMCP("agentline")
_client: Agentline | None = None


def _client_or_init() -> Agentline:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def _clamp_timeout(timeout: float) -> float:
    return max(1.0, min(float(timeout), MAX_WAIT_TIMEOUT))


# ── Phone numbers ────────────────────────────────────────────────────

@mcp.tool()
def provision_number(
    area_code: str | None = None,
    country_code: str = "US",
    phone_number: str | None = None,
) -> dict:
    """Provision a phone number the agent can use — for receiving SMS (e.g. 2FA),
    sending SMS, or placing/receiving voice calls.

    Use this BEFORE signing up for a service that asks for a phone number, or
    before making outbound calls. If `phone_number` is given, provisions that
    specific number; otherwise auto-searches by `area_code`.

    Returns a dict with `id`, `phone_number` (E.164 format — pass this to forms),
    `provider`, and `status`. Save the returned `phone_number` — you need it to
    later `release_number` or `wait_for_sms`.
    """
    try:
        result = _client_or_init().provision_number(
            phone_number=phone_number,
            area_code=area_code,
            country_code=country_code,
        )
        return asdict(result)
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def release_number(phone_number: str) -> dict:
    """Release a previously provisioned phone number. Call this when done to
    avoid ongoing Telnyx monthly charges. Pass the E.164 `phone_number` returned
    by `provision_number`.
    """
    try:
        released = _client_or_init().release_number(phone_number)
        return {"phone_number": phone_number, "released": released}
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def list_numbers() -> dict:
    """List all phone numbers currently provisioned on this account. Useful when
    the agent needs to find a number it forgot about, or audit what's active.
    """
    try:
        numbers = _client_or_init().list_numbers()
        return {"numbers": [asdict(n) for n in numbers]}
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


# ── SMS ──────────────────────────────────────────────────────────────

@mcp.tool()
def send_sms(from_number: str, to_number: str, body: str) -> dict:
    """Send an outbound SMS from a provisioned number. `from_number` must be a
    number you already provisioned; `to_number` is the recipient in E.164 format
    (e.g. "+15551234567"). Outbound US SMS, international SMS, and inbound SMS
    all work — Agentline's 10DLC campaign is approved across all major US carriers.
    """
    try:
        return _client_or_init().send_sms(from_=from_number, to=to_number, body=body)
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def wait_for_sms(
    phone_number: str,
    timeout: float = DEFAULT_WAIT_TIMEOUT,
    match: str | None = None,
) -> dict:
    """Long-poll (blocking up to `timeout` seconds, max 180) for the next inbound
    SMS on a provisioned number. Use this right AFTER submitting a form that
    triggers an SMS — call this to catch the reply.

    `match` is an optional regex (e.g. `\\d{6}` for a 6-digit code) — only
    messages matching the pattern satisfy the wait. Any inbound message satisfies
    it when `match` is None.

    Returns the message dict (with `body` and auto-extracted `extracted_code`
    when present), or `{"message": null, "status": "timeout"}` if no message
    arrived in time.
    """
    try:
        msg = _client_or_init().wait_for_sms(
            phone_number=phone_number,
            timeout=_clamp_timeout(timeout),
            match=match,
        )
        if msg is None:
            return {"message": None, "status": "timeout"}
        return {"message": asdict(msg), "status": "received"}
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def capture_code(
    area_code: str | None = None,
    timeout: float = DEFAULT_WAIT_TIMEOUT,
    release_after: bool = True,
) -> dict:
    """All-in-one 2FA capture: provision a fresh phone number, wait for an
    incoming SMS verification code (4-8 digits by default), then release the
    number. THE killer flow for signups.

    Typical use: call this, take `phone_number` from the result and paste into
    the signup form, then `code` will be the extracted 2FA code once it arrives.
    If no code arrives in `timeout` seconds, `code` is null.

    Set `release_after=False` if you plan to keep using the number.
    """
    try:
        client = _client_or_init()
        number = client.provision_number(area_code=area_code)
        try:
            code = client.get_verification_code(
                number.phone_number,
                timeout=_clamp_timeout(timeout),
            )
            return {
                "phone_number": number.phone_number,
                "code": code,
                "released": release_after,
            }
        finally:
            if release_after:
                client.release_number(number.phone_number)
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


# ── Voice calls ──────────────────────────────────────────────────────

@mcp.tool()
def make_call(
    from_number: str,
    to_number: str,
    prompt: str,
    first_message: str | None = None,
    voice: str = "aura-asteria-en",
    llm_model: str = "claude-sonnet-4-20250514",
    max_duration_seconds: int = 300,
) -> dict:
    """Place an outbound AI voice call. An AI agent answers when the recipient
    picks up and follows `prompt` as its system instructions; `first_message` is
    what it says on connect.

    Returns immediately with the `id` (call_id) — the call runs in the
    background. Poll `get_call(call_id)` to see status, transcript, and summary
    once it completes.

    `voice` is a Deepgram TTS voice (aura-asteria-en, aura-orion-en, …).
    """
    try:
        result = _client_or_init().make_call(
            from_=from_number,
            to=to_number,
            prompt=prompt,
            voice=voice,
            first_message=first_message,
            llm_model=llm_model,
            max_duration_seconds=max_duration_seconds,
            wait=False,
        )
        return asdict(result)
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def get_call(call_id: str) -> dict:
    """Get status, transcript, and summary for a call. Call this after
    `make_call` to check whether the call has completed. Terminal statuses are
    `completed`, `failed`, `no_answer`, `busy` — anything else means the call
    is still in progress and you should poll again.
    """
    try:
        result = _client_or_init().get_call(call_id)
        return asdict(result)
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def hangup_call(call_id: str) -> dict:
    """End an in-progress call immediately. No-op / error if the call already
    terminated.
    """
    try:
        return _client_or_init().hangup(call_id)
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


# ── Email ────────────────────────────────────────────────────────────

@mcp.tool()
def create_email_address(local_part: str | None = None) -> dict:
    """Provision a new email address for sending and receiving mail. Use this
    when signing up for services that require email verification — the agent
    gets a real inbox.

    `local_part` is the part before the @ (e.g. "my-agent"); leave null to
    auto-generate. Returns `id`, `email_address` (full address to paste into
    forms), `provider`, `status`.
    """
    try:
        result = _client_or_init().create_email_address(local_part=local_part)
        return asdict(result)
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def list_email_addresses() -> dict:
    """List all email addresses currently provisioned on this account."""
    try:
        addrs = _client_or_init().list_email_addresses()
        return {"addresses": [asdict(a) for a in addrs]}
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def release_email_address(address_id: str) -> dict:
    """Release a provisioned email address. Pass the `id` returned from
    `create_email_address` (NOT the full email string).
    """
    try:
        released = _client_or_init().release_email_address(address_id)
        return {"address_id": address_id, "released": released}
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def send_email(
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    body_html: str | None = None,
    reply_to: str | None = None,
) -> dict:
    """Send an outbound email from a provisioned address. `from_email` must be
    one of your provisioned addresses.
    """
    try:
        return _client_or_init().send_email(
            from_=from_email,
            to=to_email,
            subject=subject,
            body=body,
            body_html=body_html,
            reply_to=reply_to,
        )
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def wait_for_email(
    email_address: str,
    timeout: float = DEFAULT_WAIT_TIMEOUT,
    match: str | None = None,
) -> dict:
    """Long-poll (blocking up to `timeout` seconds, max 180) for the next
    inbound email on a provisioned address. Use right after triggering an email
    (e.g. a 'check your email' signup step).

    `match` is an optional regex run against the message body. Returns the
    message dict on match (includes `subject`, `body_text`, `extracted_code`),
    or `{"message": null, "status": "timeout"}` on timeout.
    """
    try:
        msg = _client_or_init().wait_for_email(
            email_address=email_address,
            timeout=_clamp_timeout(timeout),
            match=match,
        )
        if msg is None:
            return {"message": None, "status": "timeout"}
        return {"message": asdict(msg), "status": "received"}
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


@mcp.tool()
def capture_email_code(
    local_part: str | None = None,
    timeout: float = DEFAULT_WAIT_TIMEOUT,
    release_after: bool = True,
) -> dict:
    """All-in-one email verification capture: provision an email address, wait
    for an incoming verification code (4-8 digits by default), release the
    address. Use for services that email verification codes instead of SMS.

    Returns `email_address` (paste into the signup form) and `code` (the
    captured verification code). `code` is null on timeout.
    """
    try:
        client = _client_or_init()
        addr = client.create_email_address(local_part=local_part)
        try:
            code = client.get_email_verification_code(
                addr.email_address,
                timeout=_clamp_timeout(timeout),
            )
            return {
                "email_address": addr.email_address,
                "code": code,
                "released": release_after,
            }
        finally:
            if release_after:
                client.release_email_address(addr.id)
    except AgentlineError as e:
        return {"error": str(e), "status_code": e.status_code}


def main() -> None:
    """Run the stdio MCP server. Entry point for `agentline-mcp` script."""
    mcp.run()


if __name__ == "__main__":
    main()
