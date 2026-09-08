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
