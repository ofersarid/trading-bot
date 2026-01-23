---
name: Ollama Manager
description: Manage Ollama server - check status, start, stop, and list models
tags: [ollama, llm, server, ai]
---

# Ollama Server Management

This command helps you manage the Ollama server and interact with local LLM models.

## Available Operations

### 1. Check Status
Check if Ollama server is running and list available models.

**Steps:**
1. Check if Ollama process is running using `pgrep -fl ollama`
2. Test server connectivity with `ollama list`
3. Display status with clear formatting:
   - ✅ **Ollama is RUNNING** (if active)
   - ❌ **Ollama is OFF** (if not running)
4. If running, list all available models with their sizes and last modified dates

### 2. Start Ollama
Start the Ollama server in the background.

**Steps:**
1. Check if Ollama is already running (avoid duplicate processes)
2. If not running, start with: `ollama serve > /dev/null 2>&1 &`
3. Wait 2 seconds for startup
4. Verify it started successfully with `ollama list`
5. Confirm startup with message: "✅ Ollama server started successfully"

**Important:** Starting Ollama creates a background process that will continue running even after this command completes.

### 3. Stop Ollama
Stop the Ollama server gracefully.

**Steps:**
1. Find Ollama process ID with `pgrep ollama`
2. If running, kill the process: `pkill -TERM ollama`
3. Wait 1 second
4. Verify it stopped with `pgrep ollama`
5. Confirm shutdown with message: "✅ Ollama server stopped"
6. If already stopped, inform: "ℹ️ Ollama was not running"

### 4. Pull a Model
Download a new model from Ollama's registry.

**Steps:**
1. Check if Ollama is running (must be running to pull models)
2. If not running, start it first
3. Ask user which model to pull (e.g., `llama3.2`, `codellama`, `mistral`)
4. Run: `ollama pull <model-name>`
5. Show download progress
6. Confirm completion and show updated model list

### 5. Remove a Model
Delete a model to free up disk space.

**Steps:**
1. List current models
2. Ask user which model to remove
3. Run: `ollama rm <model-name>`
4. Confirm removal

---

## User Interaction Flow

When the user runs this command, ask them what they want to do:

**Present options:**
```
What would you like to do with Ollama?

1. 📊 Check status
2. ▶️  Start server
3. ⏹️  Stop server
4. ⬇️  Pull a new model
5. 🗑️  Remove a model
```

Based on their choice, execute the corresponding operation from the sections above.

---

## Common Model Names

Suggest these popular models when pulling:
- `llama3.2` - Meta's Llama 3.2 (latest)
- `llama3.2:1b` - Llama 3.2 1B (smallest, fastest)
- `llama3.2:3b` - Llama 3.2 3B (balanced)
- `codellama` - Code-specialized Llama
- `mistral` - Mistral 7B
- `mixtral` - Mixtral 8x7B MoE
- `phi3` - Microsoft Phi-3
- `qwen2.5-coder` - Qwen 2.5 for coding

---

## Error Handling

**If Ollama is not installed:**
```
⚠️ Ollama is not installed on this system.

To install Ollama:
- macOS: brew install ollama
- Linux: curl -fsSL https://ollama.com/install.sh | sh
- Manual: https://ollama.com/download
```

**If Ollama fails to start:**
- Check if port 11434 is already in use
- Check terminal output for error messages
- Suggest running `ollama serve` manually to see detailed errors

**If models fail to pull:**
- Verify internet connection
- Check available disk space
- Verify model name exists in registry

---

## Tips

- Ollama runs on `http://localhost:11434` by default
- Models are stored in `~/.ollama/models/`
- You can interact with models via: `ollama run <model-name>`
- For API access, use the REST endpoint when server is running

---

## Output Format

Use clear visual indicators:
- ✅ Success messages in green context
- ❌ Error messages in red context
- ℹ️ Info messages for status
- 📊 For listing data
- Use code blocks for command outputs
- Format model lists as tables when appropriate
