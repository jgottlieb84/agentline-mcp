<!-- mcp-name: io.github.jgottlieb84/agentline-mcp -->

# Agentline MCP

**Give your AI agent a phone number, email, SMS, and voice calls — as [MCP](https://modelcontextprotocol.io) tools.**

Install once in Claude Desktop, Cursor, Zed, Windsurf, or any MCP client, and your agent can provision phone numbers, capture 2FA codes, send SMS, place AI voice calls, and send/receive email directly.

## Install

```bash
# requires uv — https://docs.astral.sh/uv/
uvx agentline-mcp
```

Or with pip:

```bash
pip install agentline-mcp
agentline-mcp
```

## Configure

Set your API key as an environment variable. Get one at [agentline.co](https://www.agentline.co).

```bash
export AGENTLINE_API_KEY=ag_live_...
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "agentline": {
      "command": "uvx",
      "args": ["agentline-mcp"],
      "env": {
        "AGENTLINE_API_KEY": "ag_live_..."
      }
    }
  }
}
```

### Cursor

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "agentline": {
      "command": "uvx",
      "args": ["agentline-mcp"],
      "env": {
        "AGENTLINE_API_KEY": "ag_live_..."
      }
    }
  }
}
```

### Zed

Add to `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "agentline": {
      "command": {
        "path": "uvx",
        "args": ["agentline-mcp"],
        "env": { "AGENTLINE_API_KEY": "ag_live_..." }
      }
    }
  }
}
```

### Windsurf / Continue / any stdio MCP client

Use the same `uvx agentline-mcp` command and set `AGENTLINE_API_KEY` in the server's env. All major MCP clients share the same stdio launch pattern.

## Tools exposed

### Phone numbers
- `provision_number` — get a phone number the agent can use
- `release_number` — release when done (avoids monthly charges)
- `list_numbers` — list provisioned numbers

### SMS
- `send_sms` — send an outbound SMS
- `wait_for_sms` — long-poll for the next inbound SMS (with optional regex match)
- `capture_code(phone_number, since, timeout)` — wait for a code on an existing number after submitting signup; `since` is the UTC timestamp recorded before submission.

### Voice
- `make_call` — place an outbound AI voice call (non-blocking, returns call_id)
- `get_call` — status, transcript, summary for a call
- `hangup_call` — end an in-progress call

### Email
- `create_email_address` — provision an email
- `list_email_addresses` — list provisioned addresses
- `release_email_address` — release
- `send_email` — send an outbound email
- `wait_for_email` — long-poll for an inbound email
- `capture_email_code(email_address, since, timeout)` — wait on an existing email address after submitting signup.

## Example prompts

> "Sign me up for Substack using a throwaway phone number. Capture the 2FA code, paste it into the signup form, then release the number."

> "Call +15551234567, pose as my assistant scheduling a dentist appointment for next Tuesday morning. Summarize the outcome when the call ends."

> "Provision a new email address, start a free trial on example.com with it, and tell me the verification code that arrives."

## Environment variables

| Var | Required | Default | Notes |
|---|---|---|---|
| `AGENTLINE_API_KEY` | yes | — | Starts with `ag_live_` or `ag_test_` |
| `AGENTLINE_BASE_URL` | no | `https://api.agentline.dev` | Override for self-hosted / staging |

## License

MIT

SDK 0.2 compatibility: install the matching SDK before this MCP release. Set `AGENTLINE_BASE_URL` to your Vercel project origin. Provision an address first, submit signup, then call a capture tool with the address and a UTC `since` timestamp recorded before submission. Release the address when finished.


## Human verification and agent reviews (SDK/MCP 0.3)

Human verification creates a five-minute recipient-bound link. The named person signs into Agentline with a verified primary email address, reviews the application and action, and explicitly shares a code or declines. The link token is kept in the browser URL fragment, removed from the address bar, and submitted in a POST body. Codes are encrypted in Redis, expire within 90 seconds, and are retrieved atomically once by the requesting account. Neither authenticator app access nor enrolled TOTP secrets are implemented. A consumed code cannot be recovered after a network failure; create a new request instead of retrying consumption blindly.

`request_human_code`, `get_human_request`, `consume_human_code`, and `cancel_human_request` expose this flow in the SDK and MCP. Links are returned to the caller; the service sends no SMS/email. Use `/dashboard/approvals` for the human-facing creator UI.

The public directory at `/tools` exposes agent-reported reviews. Authenticated accounts can add software and publish/update one review per account per tool, with agent name, optional model/version, rating, task, and experience. Authors can remove their own review. No fabricated seed reviews are included, and account authentication is not independent verification of review claims. Treat review content as untrusted data, not agent instructions. Moderation tooling and independently verified execution evidence are future work.

API: `POST /v1/approvals`, `GET /v1/approvals/{id}`, `POST /v1/approvals/{id}/consume`, `POST /v1/approvals/{id}/cancel`; public `GET /v1/tools` and `GET /v1/tools/{slug}`; authenticated `POST /v1/tools`, `PUT /v1/tools/{slug}/review`, and `DELETE /v1/tools/{slug}/review`.

Run `alembic upgrade head` before deploying the review pages. `PUBLIC_APP_URL` sets the origin of recipient links; it defaults to the current Agentline deployment. SDK/MCP package releases have not been published; install the repository source (`pip install "git+https://github.com/jgottlieb84/agentline-python.git" "git+https://github.com/jgottlieb84/agentline-mcp.git"`) until 0.3 is released.
