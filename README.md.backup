# ai-router 🚀

> **Ultra-light AI API Router** - Zero deps, single file, auto failover

[![GitHub stars](https://img.shields.io/github/stars/longongzi/ai-router?style=social)](https://github.com/longongzi/ai-router)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Why ai-router?

Have you ever:

- 🤯 An AI API goes down and your app crashes with it
- 😤 Free API quota is exhausted, no auto-fallback to paid
- 🔄 Want to use multiple AI providers without rewriting integration for each
- 📦 Just want to make an API call without installing 500MB of dependencies

**ai-router is your answer.** One file, zero dependencies, deploy anywhere.

---

## Quick Start

### Install

```bash
pip install git+https://github.com/longongzi/ai-router.git
```

Or just download the single file:
```bash
curl -O https://raw.githubusercontent.com/longongzi/ai-router/main/ai_router.py
```

### Start

```bash
export DEEPSEEK_API_KEY="sk-your-key-here"
ai-router serve
```

### Use

OpenAI-compatible API:

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8080/v1", api_key="-")
response = client.chat.completions.create(
    model="gpt-4o-mini",  # auto-mapped to deepseek-chat
    messages=[{"role": "user", "content": "Hello!"}],
)
```

Or curl:

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

## Features

| Feature | Description |
|---------|-------------|
| 🪶 **Zero deps** | Pure Python stdlib, runs anywhere |
| 🔄 **Auto failover** | Primary down? Switch to backup |
| 🎯 **Model aliases** | Drop-in replacement for any OpenAI SDK |
| 🤝 **Multi-provider** | DeepSeek, OpenClaw, any OpenAI-compatible API |
| ⚡ **Streaming** | Native SSE streaming |
| 🐳 **Single file** | One .py, no node_modules, no venv hell |
| 📦 **CLI tools** | Built-in CLI for testing |

---

## Why ai-router?

| vs | ai-router | Alternative |
|----|-----------|-------------|
| LiteLLM | **1 file, 0 deps** | ~50MB deps |
| OpenRouter | **Self-hosted** | Hosted, privacy concerns |
| Glue code | **One solution** | Per-project wrappers |

---

## Roadmap

- [ ] Local model support (llama.cpp / Ollama)
- [ ] Load balancing
- [ ] Request caching
- [ ] Rate limiting
- [ ] Docker image

---

## Sponsor

[![Sponsor](https://img.shields.io/badge/GitHub-Sponsor-orange)](https://github.com/sponsors/longongzi)

Every sponsorship fuels continued development 🙏

---

MIT License © 2026 [longongzi](https://github.com/longongzi)

**Built with ❤️ and ☕**
