# Integrating LeRobot SO-101 with llama.cpp through the MCP

## Chapter 1: LeRobot SO-101 Installation (*Refer to [Hugging Face](https://huggingface.co/docs/lerobot/v0.5.1/en/installation)*)

On a new **Terminal**

### Step 1: Install Miniforge

Navigate to your workspace:

```bash
cd <path-to-workspace>
```

Download Miniforge:

```bash
wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
```

Make the installer executable and run it:

```bash
chmod +x Miniforge3-$(uname)-$(uname -m).sh
bash Miniforge3-$(uname)-$(uname -m).sh
```

> **Notes:**
> * Close the current terminal and open a new one so that Conda is properly initialized.
> * To disable automatic activation of the base Conda environment:
> `conda config --set auto_activate_base False`

### Step 2: Set Up the Conda Environment

Initialize Conda:

```bash
conda init --all
```

Create a Python 3.12 environment:

```bash
conda create -y -n lerobot python=3.12
```

Activate the environment:

```bash
conda activate lerobot
```

Install FFmpeg:

```bash
conda install -y -c conda-forge ffmpeg
```

### Step 3: Install LeRobot

Install system dependencies:

```bash
sudo apt update
sudo apt install -y  \
  cmake              \
  build-essential    \
  python3-dev        \
  pkg-config         \
  libavformat-dev    \
  libavcodec-dev     \
  libavdevice-dev    \
  libavutil-dev      \
  libswscale-dev     \
  libswresample-dev  \
  libavfilter-dev
```

> **Notes:**
> * Follow "Option #1" if planned to contribute to the code.
> * Follow "Option #2" if not planned to contribute to the code.

#### Option 1: Installation from source

Clone the repository:

```bash
git clone https://github.com/huggingface/lerobot.git
cd lerobot
```

Install the library in editable mode:

```bash
pip install -e .
```

#### Option 2: Installation from PyPI

```bash
pip install lerobot
```

> **Note:**
> This installs only the default dependencies.

```bash
pip install 'lerobot[all]'
```

> **Note:**
> This installs all available features.

## Chapter 2: llama.cpp Installation on Ubuntu (*Refer to [llama.cpp](https://github.com/ggml-org/llama.cpp)*)

On a new **Terminal**

### Step 1: Install Build Tools

```bash
sudo apt update
sudo apt install -y git build-essential cmake
```

### Step 2: Clone the llama.cpp Repository

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
```

### Step 3: Create the Build Directory

```bash
mkdir -p build/bin
```

### Step 4: Download a Prebuilt Binary

Download the most recent and suitable package from the llama.cpp [releases page](https://github.com/ggml-org/llama.cpp/releases).

For my lazy people, available package options from llama.cpp include:

[Ubuntu x64 (CPU)](https://github.com/ggml-org/llama.cpp/releases/download/b9628/llama-b9628-bin-ubuntu-x64.tar.gz)

[Ubuntu arm64 (CPU)](https://github.com/ggml-org/llama.cpp/releases/download/b9628/llama-b9628-bin-ubuntu-arm64.tar.gz)

[Ubuntu s390x (CPU)](https://github.com/ggml-org/llama.cpp/releases/download/b9628/llama-b9628-bin-ubuntu-s390x.tar.gz)

[Ubuntu x64 (Vulkan)](https://github.com/ggml-org/llama.cpp/releases/download/b9628/llama-b9628-bin-ubuntu-vulkan-x64.tar.gz)

[Ubuntu arm64 (Vulkan)](https://github.com/ggml-org/llama.cpp/releases/download/b9628/llama-b9628-bin-ubuntu-vulkan-arm64.tar.gz)

[Ubuntu x64 (ROCm 7.2)](https://github.com/ggml-org/llama.cpp/releases/download/b9628/llama-b9628-bin-ubuntu-rocm-7.2-x64.tar.gz)

[Ubuntu x64 (OpenVINO)](https://github.com/ggml-org/llama.cpp/releases/download/b9628/llama-b9628-bin-ubuntu-openvino-2026.0-x64.tar.gz)

[Ubuntu x64 (SYCL FP32)](https://github.com/ggml-org/llama.cpp/releases/download/b9628/llama-b9628-bin-ubuntu-sycl-fp32-x64.tar.gz)

[Ubuntu x64 (SYCL FP16)](https://github.com/ggml-org/llama.cpp/releases/download/b9628/llama-b9628-bin-ubuntu-sycl-fp16-x64.tar.gz)

> **Note:**
> This is NOT updated since Jun 14 (version: llama-b9628).

Once finised, extract the downloaded archive and navigate to the extracted `llama-bXXXX` directory.

Copy all files into the llama.cpp build directory:

```bash
cp -rf * <path-to-llama.cpp>/build/bin/
```

### Step 5: Run llama.cpp

Navigate to the build directory:

```bash
cd <path-to-llama.cpp>/build/bin
```

#### Option 1: Start the OpenAI-Compatible Server

```bash
./llama-server -hf unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL --ui-mcp-proxy
```

> **Notes:**
> * The default server port is **8080**.
> * `--ui-mcp-proxy` is required to use MCP servers through the built-in web UI.

After startup, open:

```text
http://localhost:8080
```

#### Option 2: Run Inference from the Terminal

```bash
./llama-cli -hf unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL
```

> **Notes:**
> * The model is downloaded automatically on first launch.
> * Any compatible GGUF model from Hugging Face can be used by replacing the model identifier.

#### Common Parameters

```bash
--host 0.0.0.0 # Accept connections from any network interface
--port 2424    # Listen on TCP port 2424
--ui-mcp-proxy # Enable MCP server integration in the web UI
-c 20480       # Context window size (20,480 tokens)
-ngl 999       # Offload as many layers as possible to the GPU
-t 16          # Number of CPU worker threads
...
```

## Chapter 3: MCP Installation

This chapter builds upon and extends work by *[Ilia Larchenko](https://github.com/IliaLarchenko)*.

Modifications and additions have been made to adapt the software for MCP integration, deployment workflows, and the functionality described in this repository.

Original work: *[robot_mcp](https://github.com/IliaLarchenko/robot_MCP)*

On a new **Terminal**

### Step 1: Activate the LeRobot Environment

```bash
conda activate lerobot
```

### Step 2: Navigate to the LeRobot Directory

```bash
cd <path-to-lerobot>/lerobot
```

### Step 3: Install LeRobot SO-101 MCP

Clone the repository:

```bash
git clone https://github.com/hnguyen2402/lerobot-so-101-mcp.git
cd lerobot-so-101-mcp
```

### Step 4: Create a Python Virtual Environment

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Step 5: Connect to the LeRobot SO-101

Check the current robot position:

```bash
python check_positions.py
```

Control the robot using the keyboard:

```bash
python keyboard_controller.py
```

### Step 6: Start the MCP Server

Run the Streamable HTTP transport server:

```bash
mcp run mcp_robot_server.py --transport streamable-http
```

### Step 7: Configure the MCP Server in llama.cpp

Once the llama.cpp server is running:

1. Open the llama.cpp Web UI:

  `http://localhost:<port>/`

   Default `<port>` is **8080**

2. Navigate to **MCP Servers**.
3. Add the LeRobot SO-101 MCP server:

   `http://127.0.0.1:<port>`

   Default `<port>` is **4001**

4. Enable **Use llama-server proxy**
5. Hit **Update**
6. Verify that the server status shows **Connected**.

# DONE!
