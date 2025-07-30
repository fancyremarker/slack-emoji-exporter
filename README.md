# Slack Emoji Exporter

A simple Python tool to export custom emojis from one Slack workspace to another.

## Features

- List all custom emojis in a Slack workspace
- Download emoji images locally
- Upload emojis to another Slack workspace
- Complete export from one workspace to another in a single command

## Prerequisites

- Python 3.6+
- Slack API token for the source workspace (with `emoji:read` scope)
- Session cookie from the destination workspace (for uploading)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/fancyremarker/slack-emoji-exporter.git
cd slack-emoji-exporter
```

2. Install required dependencies (using uv and a venv):
```bash
uv venv
uv pip install -r requirements.txt
uv run ./slack_emoji_exporter.py
```

## Usage

### Basic Commands

The tool provides several commands:

- `list`: List all custom emojis in a Slack workspace
- `download`: Download emoji images from a Slack workspace
- `upload`: Upload emoji images to a Slack workspace
- `export`: Complete export from source to destination workspace

### Authentication

For **reading emojis** from a workspace, you need a Slack API token:

1. Create a Slack app at https://api.slack.com/apps
2. Add the `emoji:read` permission scope
3. Install the app to your workspace
4. Use the Bot User OAuth Token (`xoxb-...`)

For **uploading emojis** to a workspace, you need a session cookie:

1. Log in to the destination Slack workspace in your browser
2. Open Developer Tools (F12 or right-click > Inspect)
3. Go to the Network tab
4. Reload the page and look for any request to slack.com
5. In the request headers, find the `Cookie` header and copy its full value
6. From the request form data, find the `token` parameter and copy its full value (it should start with xoxc-)

### Examples

#### List all custom emojis

```bash
python slack_emoji_exporter.py list --source-token xoxb-your-token-here
```

#### Download emoji images

```bash
python slack_emoji_exporter.py download --source-token xoxb-your-token-here
```

#### Upload emojis to another workspace

```bash
python slack_emoji_exporter.py upload --cookie "your-cookie-value-here" --token "xoxc-your-token-here" --team-id T012AB3C4
```

#### Complete export process

```bash
python slack_emoji_exporter.py export --source-token xoxb-your-token-here --cookie "your-cookie-value-here" --team-id T012AB3C4
```

### Finding Your Team ID

The Team ID is part of your Slack workspace URL. For example, if your Slack URL is `https://example.slack.com`, you can find the Team ID by:

1. Open your workspace in a browser
2. Look at any API request in the Network tab of Developer Tools
3. The Team ID starts with "T" followed by alphanumeric characters (e.g., T012AB3C4)

Alternatively, you can extract it from your workspace URL after logging in, where it appears as part of the path.

## Limitations

- Rate limiting: Slack may rate-limit many emoji uploads in a short period
- Large workspaces: If you have hundreds of emojis, the process may take some time
- Authentication: The session cookie method for uploading is unofficial and may change if Slack updates their interface

## License

MIT