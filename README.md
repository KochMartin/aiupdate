# aiupdate

Update all your AI coding tools in parallel with a beautiful live status display.

## Overview

`aiupdate` is a Python utility that updates multiple AI coding assistant CLI tools simultaneously, showing real-time progress and version changes.

## Features

- **Parallel Updates**: Updates all tools concurrently for speed
- **Live Status Display**: Real-time progress updates using Rich
- **Version Tracking**: Shows before/after versions for each tool
- **Error Handling**: Detailed failure reports for troubleshooting

## Supported Tools

- **codex** - OpenAI Codex CLI (`@openai/codex`)
- **gemini** - Google Gemini CLI (`@google/gemini-cli`)
- **crush** - Crush CLI (via Homebrew)
- **claude** - Claude Code CLI (local installation)

## Requirements

- Python 3.10 or higher
- `uv` (recommended) or `pip` for installation
- The AI tools you want to update should already be installed

## Installation

### Using uv (recommended)

```bash
uv pip install git+https://github.com/KochMartin/aiupdate.git
```

### Using pip

```bash
pip install git+https://github.com/KochMartin/aiupdate.git
```

### From source

```bash
git clone https://github.com/KochMartin/aiupdate.git
cd aiupdate
uv pip install -e .
```

## Usage

Simply run:

```bash
aiupdate
```

The tool will:
1. Check current versions of all installed tools
2. Update them in parallel
3. Display live progress
4. Show final version changes and any errors

## Example Output

```
Updating AI tools...

Checking current versions...
codex     updating...
gemini    updating...
crush     updating...
claude    updating...

Checking new versions...

codex     done    1.2.3 -> 1.2.4
gemini    done    2.0.1 -> 2.0.1
crush     done    0.5.0 -> 0.6.0
claude    done    1.1.0 -> 1.1.0

All 4 tools updated successfully.
```

## License

MIT
