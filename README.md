# MEOWCLI
![meowmeow](cli.png)

MEOWCLI is an open-source AI agent that brings the power of Claude, Groq, Gemini and 1000+ models directly into your terminal. It provides lightweight access to LLMs, giving you the most direct path from your prompt to the model.

## Features

- Chat with LLM models directly from your terminal
- Support for multiple providers: `g4f`, `openrouter`, `gemini`
- Convenient agent mode: work with files, directories and shell commands
- Display available models and set default model selection

## Installation

### Install from GitHub (Recommended)

```bash
pip install git+https://github.com/QWKiks/meow.git
```

### Alternative installation methods

```bash
# Clone and install locally
git clone https://github.com/QWKiks/meow.git
cd MEOWCLI
pip install -e .

# Or using pipx (for isolated environment)
pipx install git+https://github.com/QWKiks/meow.git
```

## Starting

After installation, use the `meowcli` command from any directory:

```bash
meowcli
```

On first run, a configuration file will be created in `AppData\Roaming\meowcli\config.json` with basic provider configuration.

## Command Reference

```text
┌───────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────┐
│ Command                                       │ Description                                                        │
├───────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
│ /help                                         │ Show this help message                                             │
│ /models                                       │ Show list of available models for current provider                  │
│ /chat [model_name]                            │ Start chat with AI agent. If model not specified, uses default      │
│                                               │ model for current provider.                                        │
│ /settings show                                │ Show current settings                                              │
│ /settings set provider <provider_name>        │ Set default provider (base, openrouter, gemini)                     │
│ /settings set api_key <provider_name> <key>   │ Set API key for specified provider                                 │
│ /settings set model <provider_name> <model>   │ Set default model for specified provider                           │
│ /exit                                         │ Exit the program                                                   │
└───────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────┘
```

## Configuration

Configuration is stored in `AppData\Roaming\meowcli\config.json`. Example structure: default_provider - provider, api_key - your API key, default-model - agent model.

```json
{
  "default_provider": "base",
  "providers": {
    "base": { "api_key": "", "model": "default-model" },
    "openrouter": { "api_key": "", "model": "default-model" },
    "gemini": { "api_key": "", "model": "default-model" }
  }
}
```

## Configuration Location

- **Windows**: `%APPDATA%\meowcli\config.json`
- **Linux/Mac**: `~/.config/meowcli/config.json`

## Agentic Mode

In `/chat` mode, the AI agent can:
- Browse directory contents
- Read and write files
- Execute shell commands
- Ask clarifying questions and provide final answers

## Providers

- **base**: Free models using g4f library
- **openrouter**: Access to multiple models through OpenRouter API
- **gemini**: Google's Gemini models