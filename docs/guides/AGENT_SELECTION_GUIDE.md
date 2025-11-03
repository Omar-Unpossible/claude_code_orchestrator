# Agent Selection Guide

**Quick Answer**: Use **Local Agent** (recommended for most users)

---

## When to Use Which Agent

### ✅ **Use Local Agent** (`claude-code-local`)

**When**:
- Obra and Claude Code CLI run on the **same machine**
- You're using WSL2, Linux, or macOS
- You want the **simplest setup**
- You want the **lowest latency**

**Advantages**:
- ✅ Simple setup (no SSH configuration)
- ✅ Fast communication (no network overhead)
- ✅ Direct file system access
- ✅ Easier debugging (see stdin/stdout)
- ✅ No authentication needed

**Requirements**:
- Claude Code CLI installed locally
- Same environment as Obra

**Configuration**:
```yaml
agent:
  type: claude-code-local
  workspace_path: /home/user/obra-runtime/workspace
  timeout: 300
```

---

### 🌐 **Use SSH Agent** (`claude-code-ssh`)

**When**:
- Claude Code runs on a **different machine** than Obra
- You need **isolation** between Obra and execution environment
- You're running Obra on a server managing multiple VMs
- You want to execute code in a **sandboxed VM**

**Advantages**:
- ✅ Remote execution capability
- ✅ Physical isolation for security
- ✅ Can manage multiple remote agents
- ✅ Existing SSH infrastructure

**Requirements**:
- SSH access to remote machine
- SSH key authentication set up
- Claude Code CLI installed on remote machine
- Network connectivity

**Configuration**:
```yaml
agent:
  type: claude-code-ssh
  workspace_path: /home/claude/workspace

  ssh:
    host: 192.168.1.100
    port: 22
    user: claude
    key_path: ~/.ssh/id_rsa
```

---

## Architecture Comparison

### Local Agent Architecture

```
┌─────────────────────────────────────┐
│ Same Machine (e.g., WSL2)           │
│                                      │
│  ┌──────────────┐                   │
│  │   Obra       │                   │
│  └──────┬───────┘                   │
│         │                            │
│         │ subprocess                 │
│         ↓                            │
│  ┌──────────────┐                   │
│  │ Claude Code  │                   │
│  │     CLI      │                   │
│  └──────────────┘                   │
│                                      │
│  Communication: stdin/stdout pipes  │
│  Latency: <1ms                      │
└─────────────────────────────────────┘
```

### SSH Agent Architecture

```
┌─────────────────┐         ┌─────────────────┐
│ Machine A       │         │ Machine B       │
│                 │         │                 │
│  ┌──────────┐  │         │  ┌──────────┐  │
│  │  Obra    │  │         │  │ Claude   │  │
│  │          │  │  SSH    │  │  Code    │  │
│  │          ├──┼────────>│  │  CLI     │  │
│  └──────────┘  │         │  └──────────┘  │
│                 │         │                 │
└─────────────────┘         └─────────────────┘

Communication: SSH network protocol
Latency: 10-50ms (network dependent)
```

---

## LLM Location (Independent of Agent Choice)

**Important**: The LLM (Ollama + Qwen) location is **separate** from agent choice!

```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE (GPU)                                           │
│                                                              │
│  Ollama + Qwen (RTX 5090)                                   │
│  ← HTTP API ← Obra (in WSL2/VM)                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ WSL2 / VM                                             │  │
│  │                                                        │  │
│  │  Obra ─┬─→ Local Agent → Claude Code (local)         │  │
│  │        │                                               │  │
│  │        └─→ SSH Agent → Claude Code (remote)           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Both agents use Ollama on host via HTTP API:**
```yaml
llm:
  api_url: http://172.29.144.1:11434  # Host machine
```

---

## Decision Tree

```
Do you need Claude Code on a different machine?
│
├─ YES → Use SSH Agent
│         - Set up SSH keys
│         - Configure remote host
│         - Use claude-code-ssh
│
└─ NO → Use Local Agent ✅ (recommended)
         - Install Claude Code locally
         - Use claude-code-local
         - Simpler and faster
```

---

## Feature Comparison

| Feature | Local Agent | SSH Agent |
|---------|-------------|-----------|
| **Setup Complexity** | Low ✅ | High ⚠️ |
| **Latency** | <1ms ✅ | 10-50ms |
| **Network Required** | No ✅ | Yes ⚠️ |
| **SSH Keys** | Not needed ✅ | Required ⚠️ |
| **File Access** | Direct ✅ | Via SFTP |
| **Debugging** | Easy ✅ | Harder ⚠️ |
| **Remote Execution** | No ⚠️ | Yes ✅ |
| **Isolation** | Process-level | Machine-level ✅ |
| **Use Case** | Same machine | Different machines |

---

## Configuration Examples

### Example 1: Local Agent (Recommended)

```yaml
# config/config.yaml

# Agent runs locally
agent:
  type: claude-code-local
  timeout: 300
  workspace_path: /home/omarwsl/obra-runtime/workspace

  local:
    claude_command: claude  # Command to run
    startup_timeout: 30

# LLM on host machine (unchanged)
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://172.29.144.1:11434  # Host IP
```

### Example 2: SSH Agent

```yaml
# config/config.yaml

# Agent runs remotely
agent:
  type: claude-code-ssh
  timeout: 300
  workspace_path: /home/claude/workspace

  ssh:
    host: 192.168.1.100
    port: 22
    user: claude
    key_path: ~/.ssh/id_rsa
    keepalive_interval: 30

# LLM on host machine (unchanged)
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://172.29.144.1:11434  # Host IP
```

---

## Common Misconceptions

### ❌ "Local agent means LLM runs locally"
**False!** Local agent only affects where Claude Code runs. LLM can still be on a different machine (host with GPU).

### ❌ "SSH agent is more powerful"
**False!** Both agents have the same capabilities. SSH just adds remote execution.

### ❌ "I need SSH agent for security"
**Usually false!** For single-user setups, subprocess isolation is sufficient. SSH adds complexity without security benefit.

### ❌ "Local agent won't work with Ollama on host"
**False!** Local agent communicates with Ollama via HTTP API, just like SSH agent.

---

## Migration Between Agents

### Switching from SSH to Local

1. Install Claude Code CLI locally:
   ```bash
   npm install -g @anthropics/claude-code
   ```

2. Update config:
   ```yaml
   agent:
     type: claude-code-local  # Changed
     workspace_path: /home/user/workspace  # Local path
   ```

3. Remove SSH-specific config:
   ```yaml
   # Remove this section:
   # ssh:
   #   host: ...
   ```

4. Test:
   ```bash
   python -m src.cli status
   ```

### Switching from Local to SSH

1. Set up SSH access to remote machine

2. Install Claude Code CLI on remote machine

3. Update config:
   ```yaml
   agent:
     type: claude-code-ssh  # Changed
     workspace_path: /home/claude/workspace  # Remote path

     ssh:
       host: 192.168.1.100
       user: claude
       key_path: ~/.ssh/id_rsa
   ```

4. Test:
   ```bash
   python -m src.cli status
   ```

---

## Troubleshooting

### Local Agent Issues

**"Claude not found"**:
```bash
# Check Claude Code is installed
which claude

# Install if missing
npm install -g @anthropics/claude-code

# Update config if in non-standard location
agent:
  local:
    claude_command: /path/to/claude
```

**"Process hangs"**:
- Check Claude Code starts normally: `claude`
- Increase timeout in config
- Check API key is set: `echo $ANTHROPIC_API_KEY`

### SSH Agent Issues

**"Connection refused"**:
```bash
# Test SSH manually
ssh -i ~/.ssh/id_rsa user@host

# Check SSH service running
sudo systemctl status sshd  # On remote
```

**"Authentication failed"**:
```bash
# Check key permissions
chmod 600 ~/.ssh/id_rsa

# Ensure key is added
ssh-add ~/.ssh/id_rsa
```

---

## Recommendation

**For most users**: Use **Local Agent** (`claude-code-local`)

It's simpler, faster, and sufficient for typical development workflows where Obra and Claude Code run in the same environment (WSL2/Linux/macOS).

Only use SSH Agent if you specifically need remote execution or physical isolation between machines.

---

## Related Documentation

- **Implementation Plan**: `docs/development/CLAUDE_CODE_LOCAL_AGENT_PLAN.md`
- **Architecture Decision**: `docs/decisions/ADR-004-local-agent-architecture.md`
- **System Architecture**: `docs/architecture/ARCHITECTURE.md` (M2 section)
- **Setup Guide**: `docs/guides/COMPLETE_SETUP_WALKTHROUGH.md`
