# Complete Setup Walkthrough - Obra (Claude Code Orchestrator)

**End-to-End Setup Guide for Windows + Hyper-V Deployment**

This guide covers the complete setup of Obra across Windows 11 Pro host and Hyper-V VM, from installing the local LLM to executing your first autonomous task.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Part 1: Host Machine Setup](#part-1-host-machine-setup)
4. [Part 2: VM Setup (Hyper-V)](#part-2-vm-setup-hyper-v)
5. [Part 3: Network Configuration](#part-3-network-configuration)
6. [Part 4: Obra Installation (VM WSL2)](#part-4-obra-installation-vm-wsl2)
7. [Part 5: Configuration & Testing](#part-5-configuration--testing)
8. [Part 6: First Task Execution](#part-6-first-task-execution)
9. [Part 7: Remote Access Setup](#part-7-remote-access-setup-optional)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Configuration](#advanced-configuration)

---

## Architecture Overview

### Component Distribution

```
┌──────────────────────────────────────────────────────────────────┐
│  HOST MACHINE (Windows 11 Pro)                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Windows Host Services                                     │  │
│  │  ├─ Hyper-V (VM hypervisor)                               │  │
│  │  ├─ Ollama + Qwen 2.5 Coder (GPU acceleration)           │  │
│  │  └─ Network: 0.0.0.0:11434 (accessible from VM)          │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                         │ Hyper-V Internal Network
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  HYPER-V VM (Windows 11 Pro)                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  WSL2 (Ubuntu)                                             │  │
│  │  ├─ Obra Orchestrator (Python)                            │  │
│  │  ├─ Claude Code CLI (Node.js)                             │  │
│  │  ├─ SQLite Database                                        │  │
│  │  └─ Workspace Directory                                    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Windows VM (optional development tools)                         │
└──────────────────────────────────────────────────────────────────┘
```

**Key Points**:
- **Host**: Windows 11 Pro runs Ollama + Qwen (local LLM with GPU)
- **VM**: Windows 11 Pro guest with WSL2 runs Obra orchestrator
- **Isolation**: Claude Code CLI executes in isolated VM WSL2 environment
- **Communication**: VM WSL2 → Host Ollama (HTTP), no SSH needed for local setup
- **Remote**: Instructions included for accessing from fully remote machines

### Why This Architecture?

1. **GPU Access**: Host Windows has direct GPU access for Ollama
2. **Isolation**: Claude Code runs in isolated VM to prevent host changes
3. **Flexibility**: VM can be snapshotted, rolled back, or cloned
4. **Network**: Hyper-V networking allows VM to access host services
5. **Remote Ready**: Same VM can be accessed from remote machines

---

## Prerequisites

### Host Machine Requirements

- **OS**: Windows 11 Pro (Hyper-V requires Pro/Enterprise)
- **CPU**: Multi-core processor with virtualization (Intel VT-x / AMD-V)
- **RAM**: 32GB minimum (16GB host + 8GB VM + 8GB LLM)
- **GPU**: NVIDIA RTX GPU with 24GB+ VRAM (RTX 3090, RTX 4090, RTX 5090)
- **Storage**: 150GB+ free space:
  - 50GB for LLM model
  - 50GB for VM
  - 50GB for workspace
- **Network**: Internal (Hyper-V) or external (remote access)

### VM Requirements

- **OS**: Windows 11 Pro (same as host)
- **CPU**: 4+ cores allocated
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB+ VHD
- **Network**: Hyper-V Default Switch or External Network

### Software Prerequisites

**Host (Windows 11 Pro)**:
- Hyper-V enabled
- NVIDIA GPU drivers (latest, CUDA support)
- Ollama for Windows

**VM (Windows 11 Pro + WSL2)**:
- WSL2 enabled
- Ubuntu 22.04 in WSL2
- Node.js 18+ (for Claude Code CLI)
- Python 3.10+ (for Obra)
- Git

---

## Part 1: Host Machine Setup

### Step 1.1: Enable Hyper-V

**PowerShell as Administrator**:

```powershell
# Enable Hyper-V
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# Restart computer when prompted
```

**Verify Hyper-V**:

```powershell
# After restart
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V
# State should be: Enabled
```

**Alternative (GUI)**:
1. Open "Turn Windows features on or off"
2. Check "Hyper-V"
3. Click OK and restart

### Step 1.2: Install NVIDIA GPU Drivers

**Download and Install**:
1. Go to https://www.nvidia.com/Download/index.aspx
2. Select your GPU (e.g., GeForce RTX 5090)
3. Download "Game Ready Driver" or "Studio Driver"
4. Run installer
5. Restart computer

**Verify Installation**:
```powershell
nvidia-smi
```

**Expected output**:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 560.xx       Driver Version: 560.xx       CUDA Version: 12.x    |
|-------------------------------+----------------------+----------------------+
| GPU  Name            TCC/WDDM | Bus-Id        Disp.A | Volatile Uncorr. ECC |
|   0  NVIDIA GeForce RTX 5090  |   0000:01:00.0    On |                  N/A |
+-------------------------------+----------------------+----------------------+
```

### Step 1.3: Install Ollama (Local LLM Runtime)

**On Windows Host** (NOT in WSL2):

1. **Download Ollama**:
   - Go to https://ollama.ai/download
   - Download "Download for Windows"
   - Run `OllamaSetup.exe`

2. **Verify Installation**:
   ```powershell
   ollama --version
   # Output: ollama version 0.x.x
   ```

3. **Configure Ollama for Network Access**:

   By default, Ollama only listens on `127.0.0.1` (localhost). To allow VM access:

   ```powershell
   # PowerShell as Administrator
   [Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")
   ```

4. **Restart Ollama**:
   - Right-click Ollama icon in system tray → Exit
   - Search "Ollama" in Start menu → Launch

5. **Verify Ollama is Listening**:
   ```powershell
   netstat -an | findstr "11434"
   # Should show: 0.0.0.0:11434
1. PS C:\Windows\System32> netstat -an | findstr "11434"
  TCP    127.0.0.1:1481         127.0.0.1:11434        ESTABLISHED
  TCP    127.0.0.1:11434        0.0.0.0:0              LISTENING
  TCP    127.0.0.1:11434        127.0.0.1:1481         ESTABLISHED
   ```

### Step 1.4: Download Qwen 2.5 Coder Model

**This will take 30-60 minutes (model is ~18GB)**

```powershell
ollama pull qwen2.5-coder:32b
```

**Monitor download progress**:
```
pulling manifest
pulling 8934d96d3f08... 100% ▕████████████▏ 19 GB
pulling 8c17c2ebb0ea... 100% ▕████████████▏ 7.0 KB
...
success
```

**Verify Download**:
```powershell
ollama list
# Output:
# NAME                     ID              SIZE      MODIFIED
# qwen2.5-coder:32b        abc123...       18 GB     2 minutes ago
```

**Test the Model**:
```powershell
ollama run qwen2.5-coder:32b "Write a hello world function in Python"
```

You should see a Python function generated. Press `Ctrl+D` or type `/bye` to exit.

### Step 1.5: Get Host IP Address

**Find your host IP that VM will use**:

```powershell
# Get all IP addresses
ipconfig

# Look for "Ethernet adapter vEthernet (Default Switch)" or your network adapter
# Note the IPv4 address (e.g., 192.168.1.10)
```

**For Hyper-V Default Switch** (VM-to-Host communication):
- The host is typically accessible via the gateway IP
- Example: If VM gets `172.24.128.x`, host is usually `172.24.128.1`

---

## Part 2: VM Setup (Hyper-V)

### Step 2.1: Create Windows 11 Pro VM

**Option A: Hyper-V Manager (GUI)**

1. Open **Hyper-V Manager**
2. Click **Action** → **New** → **Virtual Machine**
3. **Configuration**:
   - Name: `obra-vm` or `claude-code-vm`
   - Generation: **Generation 2** (UEFI, better performance)
   - Memory: **8192 MB** (8GB), enable Dynamic Memory
   - Network: **Default Switch** (or create External Switch for remote access)
   - Virtual Hard Disk: **50 GB** minimum
   - Installation: Point to Windows 11 ISO

4. **Before starting VM**:
   - Right-click VM → Settings
   - **Processor**: Assign 4+ virtual processors
   - **Security**: Disable Secure Boot (for easier testing)
   - **Checkpoints**: Enable (for snapshots)

5. **Install Windows 11 Pro** in VM:
   - Start VM
   - Follow Windows setup
   - Choose Windows 11 **Pro** edition
   - Complete initial setup

**Option B: PowerShell**

```powershell
# PowerShell as Administrator

# Create VM
New-VM -Name "obra-vm" -MemoryStartupBytes 8GB -Generation 2 -NewVHDPath "C:\Hyper-V\obra-vm.vhdx" -NewVHDSizeBytes 50GB -SwitchName "Default Switch"

# Configure VM
Set-VM -Name "obra-vm" -ProcessorCount 4 -DynamicMemory -MemoryMinimumBytes 4GB -MemoryMaximumBytes 16GB

# Attach Windows ISO
Add-VMDvdDrive -VMName "obra-vm" -Path "C:\ISOs\Win11_EnglishInternational_x64.iso"

# Start VM and install Windows
Start-VM -Name "obra-vm"

# Connect to VM console
vmconnect localhost "obra-vm"
```

### Step 2.2: Enable WSL2 in VM

**Inside the VM (Windows 11 Pro)**:

1. **Open PowerShell as Administrator** (in VM):

```powershell
# Enable WSL2
wsl --install

# This will:
# - Enable WSL and Virtual Machine Platform
# - Download and install Ubuntu (default)
# - Restart VM (required)
```

2. **Restart the VM**

3. **After restart, Ubuntu setup will launch**:
   - Create username (e.g., `obra`)
   - Create password
   - Wait for installation to complete

4. **Verify WSL2**:
```powershell
wsl --list --verbose
# Output:
#   NAME      STATE           VERSION
# * Ubuntu    Running         2
```

### Step 2.3: Install Development Tools in VM WSL2

**Open Ubuntu (WSL2) in the VM**:

```bash
# Update package lists
sudo apt update

# Install essential tools
sudo apt install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    curl \
    build-essential \
    ca-certificates

# Verify Python
python3 --version
# Output: Python 3.10.x
```

### Step 2.4: Install Node.js in VM WSL2

**Claude Code CLI requires Node.js 18+**:

```bash
# Install Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version   # Should show v20.x.x
npm --version    # Should show v10.x.x
```

### Step 2.5: Install Claude Code CLI in VM WSL2

```bash
# Install globally
sudo npm install -g @anthropics/claude-code

# Verify installation
claude --version
# Output: @anthropics/claude-code vX.X.X
```

**Configure Claude API Key**:

```bash
# Get your API key from: https://console.anthropic.com/

# Set environment variable (permanent)
echo 'export ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $ANTHROPIC_API_KEY
```

**Test Claude Code CLI**:

```bash
claude --help
# Should show help menu
```

### Step 2.6: Create Workspace Directory in VM WSL2

```bash
# Create workspace for Claude Code execution
mkdir -p ~/obra-workspace
cd ~/obra-workspace

# Set permissions
chmod 755 ~/obra-workspace
```

---

## Part 3: Network Configuration


### Network Topology
```
┌─────────────────────────────────────────────────────────┐
│ HOST MACHINE                                            │
│                                                         │
│  Ollama Service: 0.0.0.0:11434                         │
│  DevSwitch IP: 10.0.75.1                               │
│                                                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Hyper-V DevSwitch Network
                     │
┌────────────────────▼────────────────────────────────────┐
│ VM WINDOWS                                              │
│                                                         │
│  Ethernet 3: 10.0.75.2 (→ Host: 10.0.75.1)            │
│  WSL Adapter: 172.29.144.1 (→ VM WSL2)                │
│                                                         │
│  Port Forward: 172.29.144.1:11434 → 10.0.75.1:11434   │
│                                                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ WSL Network
                     │
┌────────────────────▼────────────────────────────────────┐
│ VM WSL2                                                 │
│                                                         │
│  IP: 172.29.147.188                                    │
│  Gateway: 172.29.144.1                                 │
│                                                         │
│  Ollama Access: http://172.29.144.1:11434              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Connection Path:**
VM WSL2 (172.29.147.188) → VM Windows (172.29.144.1:11434) → Host (10.0.75.1:11434) → Ollama


### Step 3.1: Get VM IP Address

**In VM WSL2**:

```bash
# Get WSL2 IP (inside VM)
hostname -I
172.29.147.188
# Example output: 172.24.128.5
```

**Get VM Windows IP** (if needed):

## Host IPs
Wireless LAN adapter Wi-Fi 2
192.168.1.21

Ethernet adapter vEthernet (Default Switch)
172.22.176.1

```powershell
# In VM Windows (PowerShell)
ipconfig | findstr IPv4
# Look for "Ethernet adapter vEthernet"
   IPv4 Address. . . . . . . . . . . : 10.0.75.2
   IPv4 Address. . . . . . . . . . . : 172.29.144.1
```

### Step 3.2: Find Host IP from VM

**In VM WSL2**:

```bash
# Get Windows host IP (as seen from VM WSL2)
cat /etc/resolv.conf | grep nameserver | awk '{print $2}'
10.255.255.254
# Example output: 172.24.128.1
```

This is the IP to use for Ollama connection.

### Step 3.3: Test Connectivity

**Test VM → Host Ollama connection**:

```bash
# From VM WSL2, use VM Windows as proxy
curl http://172.29.144.1:11434/api/tags

# Example:
curl http://172.24.128.1:11434/api/tags
```

**Expected output** (JSON with models):
```json
{
  "models": [
    {
      "name": "qwen2.5-coder:32b",
      "modified_at": "2025-11-01T...",
      "size": 19000000000,
      ...
    }
  ]
}
```

**If connection fails**:

1. **Check Windows Firewall on Host**:
   ```powershell
   # On host, PowerShell as Admin
   New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 11434
   ```

2. **Verify Ollama is listening on 0.0.0.0**:
   ```powershell
   # On host
   netstat -an | findstr "11434"
   # Should show: 0.0.0.0:11434
   ```

---

## Part 4: Obra Installation (VM WSL2)

### Step 4.1: Clone Obra Repository

**In VM WSL2**:

```bash
# Navigate to home directory
cd ~

# Create projects directory
mkdir -p projects
cd projects

# Clone repository
git clone <repository-url> obra
cd obra

# Or if you're developing locally:
# git clone https://github.com/yourusername/claude_code_orchestrator.git obra
```

### Step 4.2: Run Automated Setup

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh
```

**Setup script will**:
- ✓ Check Python 3.10+
- ✓ Create virtual environment
- ✓ Install dependencies
- ✓ Create directories (data, logs)
- ✓ Initialize database
- ✓ Optionally run tests

**When prompted**:
- Install dev dependencies? → `y` (recommended)
- Setup Ollama? → `n` (already on host)
- Download Qwen model? → `n` (already on host)
- Run tests? → `y` (optional, verify installation)

### Step 4.3: Activate Virtual Environment

```bash
source venv/bin/activate
```

Your prompt should change to `(venv) username@hostname:~/projects/obra$`

### Step 4.4: Verify Installation

```bash
# Check Python packages
pip list | grep -E "sqlalchemy|click|pyyaml|requests"

# Should show:
# click          8.1.x
# PyYAML         6.0.x
# requests       2.31.x
# SQLAlchemy     2.0.x
```

---

## Part 5: Configuration & Testing

### Step 5.1: Get Required IP Addresses

**In VM WSL2**:

```bash
# Get host IP (for Ollama)
HOST_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
echo "Host IP (Ollama): $HOST_IP"

# Get VM WSL2 IP (for reference)
VM_IP=$(hostname -I | awk '{print $1}')
echo "VM WSL2 IP: $VM_IP"
```

### Step 5.2: Configure Obra

**Edit configuration file**:

```bash
cd ~/projects/obra
nano config/config.yaml
```

**Update with these values**:

```yaml
database:
  url: sqlite:////home/omarwsl/obra-runtime/data/orchestrator.db

agent:
  type: claude_code  # Claude Code CLI agent
  config:
    # For local (same machine) - no SSH needed
    execution_mode: local
    workspace_dir: /home/omarwsl/obra-runtime/workspace
    timeout: 300
    max_retries: 3

llm:
  provider: ollama
  model: qwen2.5-coder:32b
  base_url: http://172.24.128.1:11434  # Replace with your HOST_IP
  temperature: 0.1
  timeout: 120

orchestration:
  breakpoints:
    confidence_threshold: 0.7
    max_retries: 3

  decision:
    high_confidence: 0.85
    medium_confidence: 0.65
    low_confidence: 0.4

  quality:
    min_quality_score: 0.7
    enable_syntax_validation: true
    enable_testing_validation: false
    enable_requirements_validation: true

  scheduler:
    max_concurrent_tasks: 1

utils:
  token_counter:
    default_model: qwen2.5-coder

  context_manager:
    max_tokens: 100000
    summarization_threshold: 50000

  confidence_scorer:
    ensemble_weight_heuristic: 0.4
    ensemble_weight_llm: 0.6

logging:
  level: INFO
  file: /home/omarwsl/obra-runtime/logs/orchestrator.log
  max_size: 100MB
  backup_count: 5
```

**Save and exit** (Ctrl+X, Y, Enter)

### Step 5.3: Test LLM Connection

```bash
# Test Ollama API
curl http://$HOST_IP:11434/api/tags | jq .

# Test with Python
python3 << 'EOF'
import requests
import json

response = requests.post(
    'http://172.24.128.1:11434/api/generate',  # Replace with HOST_IP
    json={
        'model': 'qwen2.5-coder:32b',
        'prompt': 'Write a hello world function',
        'stream': False
    },
    timeout=30
)

print(json.dumps(response.json(), indent=2))
EOF
```

### Step 5.4: Initialize Obra

```bash
python -m src.cli init
```

**Expected output**:
```
Initializing Obra orchestrator...
✓ Database initialized: sqlite:///orchestrator.db
✓ Created directories: data/, logs/
✓ Configuration validated
✓ Obra initialized successfully!
```

### Step 5.5: Verify Configuration

```bash
# Check Obra status
python -m src.cli status
```

**Expected output**:
```
Obra Orchestrator Status
================================================================================
Version: 1.0.0
Database: sqlite:///orchestrator.db (connected)
LLM: qwen2.5-coder:32b (Ollama @ http://172.24.128.1:11434)
Agent: claude_code (local mode)

Projects: 0
Tasks:
  Pending: 0
  In Progress: 0
  Completed: 0
  Total: 0
```

---

## Part 6: First Task Execution

### Step 6.1: Create Your First Project

```bash
python -m src.cli project create "Hello Obra" \
  --description "Testing the Obra orchestrator"
```

**Output**:
```
✓ Created project #1: Hello Obra
  Description: Testing the Obra orchestrator
  Working directory: /home/obra/obra-workspace
```

### Step 6.2: Create a Test Task

```bash
python -m src.cli task create "Write a hello world function" \
  --project 1 \
  --description "Create a Python function that prints 'Hello, World!'" \
  --priority 10
```

**Output**:
```
✓ Created task #1: Write a hello world function
  Project: #1 (Hello Obra)
  Priority: 10
  Status: pending
```

### Step 6.3: Execute the Task

```bash
python -m src.cli task execute 1 --max-iterations 5
```

**What happens** (10-step orchestration loop):

1. **Load Task**: Obra retrieves task #1 from database
2. **Build Context**: ContextManager gathers relevant information
3. **Generate Prompt**: PromptGenerator creates optimized prompt
4. **Send to LLM**: Prompt sent to Qwen (validation/oversight)
5. **Execute with Agent**: Claude Code CLI executes in workspace
6. **Monitor Output**: Tracks execution progress
7. **Validate Response**: ResponseValidator checks format/completeness
8. **Quality Check**: QualityController validates correctness
9. **Score Confidence**: ConfidenceScorer rates confidence (0-1)
10. **Decide Action**: DecisionEngine decides next step (proceed/retry/escalate)

**Expected output**:
```
Executing task #1: Write a hello world function...

[INFO] Loading task from database...
[INFO] Building context (0 prior iterations)...
[INFO] Generating prompt for Qwen validation...
[INFO] Sending prompt to LLM (Ollama)...
[INFO] LLM validation score: 0.85 (high confidence)
[INFO] Executing with Claude Code CLI...
[INFO] Monitoring output...
[INFO] Validating response format...
[INFO] Quality validation score: 0.92
[INFO] Confidence score: 0.89 (high)
[INFO] Decision: PROCEED

================================================================================
Task #1 execution result:
================================================================================
Status: completed
Iterations: 1
Quality Score: 0.92
Confidence: 0.89
Execution Time: 12.3s

✓ Task completed successfully!
```

### Step 6.4: View Task Details

```bash
# List all tasks
python -m src.cli task list

# View specific task
python -m src.cli task show 1
```

**Output**:
```
Task #1: Write a hello world function
================================================================================
Status: completed
Project: #1 (Hello Obra)
Priority: 10
Created: 2025-11-01 15:30:00
Completed: 2025-11-01 15:30:15

Description:
  Create a Python function that prints 'Hello, World!'

Execution Summary:
  Iterations: 1
  Quality Score: 0.92
  Confidence: 0.89
  Execution Time: 12.3s

Output:
  def hello_world():
      """Print a friendly greeting."""
      print("Hello, World!")

  # Test the function
  hello_world()
```

### Step 6.5: Check Overall Status

```bash
python -m src.cli status
```

**Output**:
```
Obra Orchestrator Status
================================================================================
Projects: 1
Tasks:
  Pending: 0
  In Progress: 0
  Completed: 1
  Failed: 0
  Total: 1

Recent Activity:
  - Task #1 completed (12s ago) - Quality: 0.92, Confidence: 0.89
```

### Step 6.6: Try Interactive Mode

```bash
python -m src.cli interactive
```

**Interactive session**:
```
Obra Interactive Mode
Type 'help' for available commands, 'exit' to quit.

obra> use 1
✓ Using project #1: Hello Obra

obra[project:1]> task create "Write a fibonacci function"
✓ Created task #2: Write a fibonacci function

obra[project:1]> execute 2
Executing task #2...
✓ Task completed successfully! (Quality: 0.94, Confidence: 0.91)

obra[project:1]> tasks
Tasks in project #1:
  #1: Write a hello world function [completed]
  #2: Write a fibonacci function [completed]

obra[project:1]> exit
Goodbye!
```

---

## Part 7: Remote Access Setup (Optional)

This section covers accessing the VM from a **fully remote machine** (not the host).

### Scenario: Access Obra from Remote Developer Machine

```
┌─────────────────────┐
│  Developer Machine  │
│  (Remote)           │
│  - SSH Client       │
└──────────┬──────────┘
           │ SSH over internet
           ▼
┌─────────────────────┐          ┌──────────────────┐
│  Host Machine       │          │  Hyper-V VM      │
│  (Windows 11 Pro)   │◄────────►│  (Windows 11 Pro)│
│  - Ollama + Qwen    │ Internal │  - WSL2 + Obra   │
└─────────────────────┘          └──────────────────┘
```

### Step 7.1: Configure Hyper-V for External Access

**Option A: External Network Switch** (VM gets public/LAN IP)

1. **Hyper-V Manager** → Virtual Switch Manager
2. Create **External** virtual switch
3. Bind to physical network adapter
4. Assign to VM
5. VM will get IP from your network DHCP

**Option B: Port Forwarding** (VM stays on internal network)

```powershell
# On host, PowerShell as Administrator

# Forward SSH port 22 to VM
netsh interface portproxy add v4tov4 listenport=2222 listenaddress=0.0.0.0 connectport=22 connectaddress=<VM_WSL2_IP>

# Example:
# netsh interface portproxy add v4tov4 listenport=2222 listenaddress=0.0.0.0 connectport=22 connectaddress=172.24.128.5
```

### Step 7.2: Enable SSH in VM WSL2

```bash
# In VM WSL2
sudo apt install -y openssh-server

# Start SSH service
sudo service ssh start

# Verify SSH is running
sudo service ssh status

# Get SSH port
sudo netstat -tlnp | grep ssh
# Should show: 0.0.0.0:22
```

### Step 7.3: Configure SSH Key Authentication

**On Remote Developer Machine**:

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "obra-remote"

# Copy public key to VM
# (Replace with actual VM IP or host:port)
ssh-copy-id obra@<VM_IP>

# Or if using port forwarding:
ssh-copy-id -p 2222 obra@<HOST_PUBLIC_IP>
```

**Test connection**:

```bash
# Direct connection (if VM has public IP)
ssh obra@<VM_IP>

# Port forwarding (if using host proxy)
ssh -p 2222 obra@<HOST_PUBLIC_IP>
```

### Step 7.4: Remote Access to Obra

**From remote machine, connect via SSH**:

```bash
ssh -p 2222 obra@<HOST_PUBLIC_IP>

# Once connected, activate Obra
cd ~/projects/obra
source venv/bin/activate

# Use Obra normally
python -m src.cli status
python -m src.cli task execute 1
```

**Or use SSH tunneling for direct CLI access**:

```bash
# Create alias on remote machine
alias obra-remote='ssh -p 2222 obra@<HOST_PUBLIC_IP> "cd ~/projects/obra && source venv/bin/activate && python -m src.cli"'

# Now use directly
obra-remote status
obra-remote task list
obra-remote task execute 1
```

### Step 7.5: Security Considerations

1. **Firewall Rules**:
   ```powershell
   # On host, only allow SSH from specific IPs
   New-NetFirewallRule -DisplayName "Obra SSH" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 2222 -RemoteAddress <YOUR_IP>
   ```

2. **SSH Hardening** (in VM WSL2):
   ```bash
   sudo nano /etc/ssh/sshd_config

   # Disable password auth
   PasswordAuthentication no

   # Only allow key auth
   PubkeyAuthentication yes

   # Disable root login
   PermitRootLogin no

   # Restart SSH
   sudo service ssh restart
   ```

3. **VPN** (recommended for production):
   - Use WireGuard or Tailscale for secure remote access
   - Avoid exposing SSH to public internet

---

## Troubleshooting

### Issue: Cannot connect to Ollama from VM

**Symptoms**:
```
Connection refused: http://172.24.128.1:11434
```

**Solutions**:

1. **Check Ollama is running on host**:
   ```powershell
   # On host Windows
   ollama list
   # Should show models
   ```

2. **Check OLLAMA_HOST environment variable**:
   ```powershell
   # On host Windows PowerShell
   [Environment]::GetEnvironmentVariable("OLLAMA_HOST", "User")
   # Should show: 0.0.0.0:11434
   ```

3. **Check Ollama is listening on all interfaces**:
   ```powershell
   # On host Windows
   netstat -an | findstr "11434"
   # Should show: 0.0.0.0:11434 (NOT 127.0.0.1:11434)
   ```

4. **Check Windows Firewall**:
   ```powershell
   # On host, PowerShell as Administrator
   New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 11434
   ```

5. **Restart Ollama**:
   - System tray → Right-click Ollama → Exit
   - Start menu → Search "Ollama" → Launch

6. **Test from host first**:
   ```powershell
   # On host Windows
   curl http://localhost:11434/api/tags
   curl http://0.0.0.0:11434/api/tags
   ```

### Issue: Claude Code CLI not found

**Symptoms**:
```
claude: command not found
```

**Solutions**:

1. **Check npm installation**:
   ```bash
   # In VM WSL2
   npm list -g | grep claude
   ```

2. **Reinstall Claude Code CLI**:
   ```bash
   sudo npm uninstall -g @anthropics/claude-code
   sudo npm install -g @anthropics/claude-code
   ```

3. **Check PATH**:
   ```bash
   echo $PATH | grep -o '/usr/local/bin'

   # Add to PATH if missing
   echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

4. **Use full path**:
   ```bash
   /usr/local/bin/claude --version
   ```

### Issue: VM cannot get IP address

**Symptoms**:
VM has no network connectivity

**Solutions**:

1. **Check Hyper-V network adapter**:
   - Hyper-V Manager → VM Settings → Network Adapter
   - Should be connected to "Default Switch" or your external switch

2. **Restart network in VM**:
   ```powershell
   # In VM Windows PowerShell
   ipconfig /release
   ipconfig /renew
   ```

3. **Check Hyper-V Virtual Switch**:
   ```powershell
   # On host
   Get-VMSwitch
   ```

### Issue: GPU not detected by Ollama

**Symptoms**:
```
Model running on CPU (very slow)
```

**Solutions**:

1. **Check nvidia-smi on host**:
   ```powershell
   nvidia-smi
   # Should show GPU
   ```

2. **Update NVIDIA drivers**:
   - Download latest from nvidia.com

3. **Reinstall Ollama**:
   - Uninstall Ollama
   - Restart
   - Reinstall Ollama
   - Ollama should auto-detect GPU

4. **Check Ollama logs**:
   ```powershell
   # Ollama logs location (Windows):
   # %LOCALAPPDATA%\Ollama\logs
   ```

### Issue: Low confidence scores on all tasks

**Symptoms**:
All tasks get confidence < 0.6, causing escalations

**Solutions**:

1. **Test LLM directly**:
   ```bash
   curl -X POST http://<HOST_IP>:11434/api/generate \
     -d '{"model":"qwen2.5-coder:32b","prompt":"test","stream":false}'
   ```

2. **Make task descriptions more specific**:
   ```bash
   # Instead of: "fix the bug"
   python -m src.cli task create "Fix IndexError on line 42 by adding bounds check"
   ```

3. **Lower confidence thresholds** (config.yaml):
   ```yaml
   orchestration:
     decision:
       high_confidence: 0.75  # Was 0.85
       medium_confidence: 0.55  # Was 0.65
   ```

4. **Check LLM is responding**:
   ```bash
   ollama run qwen2.5-coder:32b "Hello"
   # Should respond quickly
   ```

### Issue: "Orchestrator not initialized"

**Solution**:
```bash
python -m src.cli init
```

### Issue: Permission denied on workspace

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: '/home/obra/obra-workspace/...'
```

**Solution**:
```bash
# Fix permissions
chmod -R 755 ~/obra-workspace
chown -R $(whoami):$(whoami) ~/obra-workspace
```

---

## Advanced Configuration

### Using PostgreSQL Instead of SQLite

**Why PostgreSQL**:
- Better concurrency for multiple users
- Better performance for large task histories
- Production-ready

**Setup** (in VM WSL2):

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start service
sudo service postgresql start

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE obra;
CREATE USER obra WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE obra TO obra;
\q
EOF

# Update config.yaml
database:
  url: postgresql://obra:secure_password_here@localhost/obra
```

### Running Obra as a Background Service

**Create systemd service** (in VM WSL2):

```bash
# Create service file
sudo nano /etc/systemd/system/obra.service
```

**Service configuration**:

```ini
[Unit]
Description=Obra Orchestrator
After=network.target

[Service]
Type=simple
User=obra
WorkingDirectory=/home/obra/projects/obra
Environment="PATH=/home/obra/projects/obra/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/obra/projects/obra/venv/bin/python -m src.cli run --continuous

Restart=on-failure
RestartSec=10

StandardOutput=append:/home/obra/projects/obra/logs/service.log
StandardError=append:/home/obra/projects/obra/logs/service.error.log

[Install]
WantedBy=multi-user.target
```

**Enable and start**:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable obra

# Start service
sudo systemctl start obra

# Check status
sudo systemctl status obra

# View logs
journalctl -u obra -f
```

### Multi-VM Setup (Multiple Execution Environments)

For running multiple isolated Claude Code instances:

1. **Clone VM in Hyper-V**:
   - Shutdown obra-vm
   - Export VM
   - Import as obra-vm-2, obra-vm-3, etc.

2. **Configure each VM** with unique:
   - IP address
   - Workspace directory
   - SSH keys

3. **Update Obra config** to support agent pool:
   ```yaml
   agent:
     type: claude_code_pool
     instances:
       - name: vm1
         host: 172.24.128.5
         workspace: /home/obra/workspace
       - name: vm2
         host: 172.24.128.6
         workspace: /home/obra/workspace
   ```

### Monitoring and Logging

**Enable detailed logging** (config.yaml):

```yaml
logging:
  level: DEBUG  # INFO, DEBUG, WARNING, ERROR
  file: logs/obra.log
  max_size: 100MB
  backup_count: 5
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**View logs**:
```bash
# Real-time
tail -f logs/obra.log

# Search for errors
grep -i error logs/obra.log

# Last 100 lines
tail -n 100 logs/obra.log
```

**Prometheus Metrics** (future enhancement):
```yaml
monitoring:
  prometheus:
    enabled: true
    port: 9090
  metrics:
    - task_execution_time
    - llm_response_time
    - confidence_scores
    - quality_scores
```

---

## Summary Checklist

### Host Machine (Windows 11 Pro)
- [ ] Hyper-V enabled and working
- [ ] NVIDIA GPU drivers installed
- [ ] Ollama installed on Windows host
- [ ] Qwen 2.5 Coder model downloaded (~18GB)
- [ ] OLLAMA_HOST set to 0.0.0.0:11434
- [ ] Ollama accessible on network (port 11434 open)
- [ ] Firewall rule allowing port 11434

### Hyper-V VM (Windows 11 Pro)
- [ ] VM created with 8GB+ RAM, 4+ CPU cores
- [ ] WSL2 enabled in VM
- [ ] Ubuntu 22.04 installed in WSL2
- [ ] Network adapter assigned (Default Switch or External)
- [ ] VM can reach host Ollama service

### VM WSL2 Environment
- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] Claude Code CLI installed globally
- [ ] ANTHROPIC_API_KEY configured
- [ ] Git installed
- [ ] Obra repository cloned
- [ ] Virtual environment created (venv/)
- [ ] Dependencies installed (requirements.txt)
- [ ] Workspace directory created

### Obra Configuration
- [ ] config.yaml updated with correct host IP
- [ ] Database initialized (sqlite or postgresql)
- [ ] LLM connection tested (curl to Ollama)
- [ ] Configuration validated (python -m src.cli init)
- [ ] First test task executed successfully

### Optional (Remote Access)
- [ ] SSH server installed in VM WSL2
- [ ] SSH key authentication configured
- [ ] Port forwarding or external network configured
- [ ] Firewall rules for remote SSH access
- [ ] Remote connection tested

---

## Next Steps

1. **Read Documentation**:
   - `docs/guides/GETTING_STARTED.md` - User guide
   - `docs/architecture/ARCHITECTURE.md` - System design
   - `README.md` - Quick reference

2. **Experiment with Obra**:
   - Create diverse tasks (coding, debugging, refactoring)
   - Try interactive mode for rapid iteration
   - Monitor confidence scores and quality metrics

3. **Optimize Configuration**:
   - Adjust confidence thresholds for your use case
   - Tune LLM temperature for consistency
   - Configure breakpoints for oversight

4. **Production Setup**:
   - Switch to PostgreSQL for multi-user
   - Setup systemd service for auto-start
   - Configure log rotation
   - Enable Prometheus metrics (future)

5. **Scale Up**:
   - Create snapshot of working VM
   - Clone VMs for parallel execution
   - Setup agent pool for concurrent tasks

---

## Getting Help

- **Documentation**: `docs/` directory
- **Logs**: `logs/obra.log` (detailed execution logs)
- **Status Check**: `python -m src.cli status`
- **Interactive Help**: `python -m src.cli interactive` → type `help`
- **GitHub Issues**: Report bugs and feature requests

---

## Terminology

- **Obra**: The orchestration platform (this system)
- **Host**: Windows 11 Pro machine running Hyper-V and Ollama
- **VM**: Hyper-V virtual machine running Windows 11 Pro + WSL2
- **WSL2**: Windows Subsystem for Linux (Ubuntu) inside the VM
- **Ollama**: Local LLM runtime (runs on host Windows)
- **Qwen**: Alibaba's Qwen 2.5 Coder language model (32B parameters)
- **Claude Code CLI**: Anthropic's code execution agent
- **LLM**: Large Language Model (Qwen, used for validation/oversight)
- **Agent**: Execution engine (Claude Code CLI)
- **Orchestrator**: Obra's main coordination component

---

**Setup Complete!** 🎉

Your Obra orchestrator is now fully configured for autonomous software development with local LLM oversight. The Windows 11 + Hyper-V + WSL2 architecture provides isolation, GPU acceleration, and flexibility for both local and remote use.

**Architecture Summary**:
- 🖥️ **Host**: Windows 11 Pro + Ollama + Qwen (GPU-accelerated)
- 🔲 **VM**: Windows 11 Pro + WSL2 + Obra + Claude Code CLI
- 🔗 **Network**: Hyper-V networking for VM ↔ Host communication
- 🌐 **Remote**: Optional SSH access for remote development

Happy orchestrating! 🚀
