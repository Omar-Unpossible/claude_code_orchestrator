# Network Configuration Guide

**Date**: November 12, 2025
**Purpose**: Document network topology for Obra → Ollama connectivity

---

## Network Topology

```
┌─────────────────────────────────────────────────────────┐
│ Host Machine (Windows 11 Pro)                          │
│ - RTX 5090 GPU                                          │
│ - Ollama with qwen2.5-coder:32b                        │
│                                                         │
│ Network Interfaces:                                     │
│   • vEthernet (DevSwitch):    10.0.75.1                │ ← Obra connects here
│   • Wi-Fi 2 (home network):   192.168.1.21             │
│   • vEthernet (Default Switch): 172.27.160.1           │
└─────────────────────────────────────────────────────────┘
                          ↓
                 10.0.75.x network
                          ↓
┌─────────────────────────────────────────────────────────┐
│ VM (Hyper-V - Windows 11 Guest)                        │
│ - IP: 10.0.75.2                                         │
│ - Gateway: 10.0.75.1 (Host)                            │
│                                                         │
│   ┌───────────────────────────────────────────┐       │
│   │ WSL2 (Ubuntu 22.04)                        │       │
│   │ - Obra runs here                           │       │
│   │ - WSL Gateway: 172.29.144.1                │       │
│   │                                             │       │
│   │ Connects to Ollama via: 10.0.75.1:11434   │       │
│   └───────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

---

## Ollama Configuration

### Correct Endpoint
```yaml
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://10.0.75.1:11434  # ✅ Host on vEthernet DevSwitch
```

### ❌ Common Mistakes

**Wrong IP: 172.29.144.1**
- This is the WSL gateway (points to VM's Windows, not Host)
- Ollama is NOT running in the VM, it's on the Host
- Results in connection refused errors

**Wrong IP: 172.27.160.1**
- This is the Default Switch adapter
- Ollama not configured to listen on this interface
- Results in connection timeouts

---

## Testing Connectivity

### From WSL (where Obra runs)

**Quick Test**:
```bash
curl http://10.0.75.1:11434/api/tags
```

**Expected Output** (if working):
```json
{
  "models": [
    {
      "name": "qwen2.5-coder:32b",
      "size": 19851349898,
      ...
    }
  ]
}
```

**If Connection Fails**:
```bash
# Test all possible IPs
curl --connect-timeout 3 http://10.0.75.1:11434/api/tags       # ✅ Should work
curl --connect-timeout 3 http://172.29.144.1:11434/api/tags    # ❌ WSL gateway
curl --connect-timeout 3 http://172.27.160.1:11434/api/tags    # ❌ Default Switch
```

---

## Troubleshooting

### Issue: Connection Refused

**Symptoms**:
```
Connection refused to http://10.0.75.1:11434
```

**Check**:
1. Is Ollama running on Host?
   ```powershell
   # On Host (PowerShell)
   Get-Process ollama
   ```

2. Is Ollama listening on all interfaces?
   ```powershell
   # On Host
   netstat -ano | findstr :11434
   ```

3. Is Windows Firewall blocking?
   ```powershell
   # On Host - Check firewall rule
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*ollama*"}
   ```

**Fix**:
- Start Ollama: `ollama serve`
- Add firewall rule if needed

---

### Issue: Network Changed (IP Different)

**Symptoms**:
- Ollama was working, now connection refused
- Network IP changed after reboot

**Check Current IPs**:
```powershell
# On Host (PowerShell)
ipconfig

# Look for "vEthernet (DevSwitch)"
```

**Update Config**:
1. Note the new IP for vEthernet (DevSwitch)
2. Update `config/config.yaml`:
   ```yaml
   llm:
     api_url: http://<NEW_IP>:11434
   ```
3. Update `CLAUDE.md` (line 89)
4. Restart Obra

---

### Issue: WSL Can't Reach Host

**Symptoms**:
- curl works from VM Windows
- curl fails from WSL

**Check WSL Networking**:
```bash
# From WSL
ip route show

# Should show route to 10.0.75.1
```

**Fix**:
```bash
# Restart WSL networking
# From Windows (PowerShell as Admin)
wsl --shutdown
# Then restart WSL
```

---

## Verification Checklist

Before running Obra, verify:

- [ ] Ollama is running on Host
  ```powershell
  Get-Process ollama
  ```

- [ ] Host IP is correct in config
  ```bash
  grep api_url config/config.yaml
  # Should show: http://10.0.75.1:11434
  ```

- [ ] WSL can reach Ollama
  ```bash
  curl http://10.0.75.1:11434/api/tags
  ```

- [ ] Model is available
  ```bash
  curl -s http://10.0.75.1:11434/api/tags | grep qwen2.5-coder:32b
  ```

---

## Quick Reference

| Component | Location | IP | Purpose |
|-----------|----------|----|---------  |
| **Ollama (GPU)** | Host Machine | 10.0.75.1 | LLM inference with RTX 5090 |
| **VM (Hyper-V)** | Virtual Machine | 10.0.75.2 | Runs WSL2 |
| **WSL2** | Inside VM | 172.29.144.1 | Runs Obra |
| **Gateway** | VM → Host | 10.0.75.1 | Routes to Host network |

**Connection Path**:
```
Obra (WSL) → 10.0.75.1:11434 → Host → Ollama (qwen2.5-coder:32b on RTX 5090)
```

---

## Files to Update on Network Change

1. **`config/config.yaml`** (line 9)
   ```yaml
   api_url: http://10.0.75.1:11434
   ```

2. **`CLAUDE.md`** (line 89)
   ```
   - Accessed at http://10.0.75.1:11434 (Host on vEthernet DevSwitch)
   ```

3. **Restart Obra** after changes

---

## See Also

- [LLM Management Guide](../guides/LLM_MANAGEMENT_GUIDE.md) - How to switch LLMs
- [CLAUDE.md](../../CLAUDE.md) - Project overview
- [Configuration Guide](../guides/CONFIGURATION_PROFILES_GUIDE.md) - Config reference

---

**Last Verified**: November 12, 2025
**Network**: Stable (vEthernet DevSwitch on static 10.0.75.x subnet)
