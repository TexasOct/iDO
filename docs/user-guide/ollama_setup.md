# Ollama Model Integration Guide

## Introduction

iDO supports integration with locally-run Ollama models. Ollama is a lightweight local LLM runtime tool that supports various open-source models including Llama, Mistral, and Qwen.

## Prerequisites

### 1. Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or visit https://ollama.com/download for installation packages
```

### 2. Download Models

```bash
# Recommended models (balanced performance and speed)
ollama pull qwen2.5:7b          # Qwen 2.5 7B (Recommended, bilingual)
ollama pull llama3.2:3b         # Llama 3.2 3B (Fast)
ollama pull mistral:7b          # Mistral 7B (High quality)

# Vision-capable models (for screenshot analysis)
ollama pull llava:7b            # LLaVA 7B (Recommended)
ollama pull llava:13b           # LLaVA 13B (Stronger but slower)
ollama pull qwen2-vl:7b         # Qwen2-VL 7B (Strong Chinese OCR)
```

### 3. Start Ollama Service

```bash
# Ollama usually starts automatically, or start manually
ollama serve

# Verify service is running
curl http://localhost:11434/api/tags
```

## Configure Ollama in iDO

### Method 1: UI Configuration (Recommended)

1. Open iDO Settings page
2. Navigate to "Model Management" tab
3. Click "Add New Model"
4. Fill in the following information:

   **Basic Configuration**
   - **Configuration Name**: `Ollama Qwen 7B` (customizable)
   - **Provider**: `ollama`
   - **API URL**: `http://localhost:11434/v1`
   - **Model Name**: `qwen2.5:7b` (or other models you downloaded)
   - **API Key**: `ollama` (any non-empty string, Ollama doesn't validate)

   **Pricing Configuration** (Optional)
   - **Input Token Price**: `0`
   - **Output Token Price**: `0`
   - **Currency**: `USD`

5. Click "Test Connection" to verify configuration
6. Save and activate the model

### Method 2: API Configuration

```python
import requests

# Add Ollama model configuration
response = requests.post('http://localhost:8000/api/models', json={
    "name": "Ollama Qwen 7B",
    "provider": "ollama",
    "apiUrl": "http://localhost:11434/v1",
    "model": "qwen2.5:7b",
    "apiKey": "ollama",  # Any non-empty string
    "inputTokenPrice": 0.0,
    "outputTokenPrice": 0.0,
    "currency": "USD"
})

model_id = response.json()['id']

# Activate the model
requests.post(f'http://localhost:8000/api/models/{model_id}/activate')
```

## API Endpoint Options

Ollama provides two API formats:

### 1. OpenAI-Compatible Format (Recommended)

```
Endpoint: http://localhost:11434/v1/chat/completions
Format: Fully compatible with OpenAI API
```

iDO uses this format by default, no additional configuration needed.

### 2. Ollama Native Format

```
Endpoint: http://localhost:11434/api/chat
Format: Ollama native API
```

To use native format, configure:
- **API URL**: `http://localhost:11434`
- **Endpoint**: `/api/chat`

## Recommended Model Selection

### For Event Extraction and Activity Summarization

| Model | Size | Speed | Quality | Recommended Use Case |
|-------|------|-------|---------|---------------------|
| `qwen2.5:7b` | 4.7GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Bilingual, best overall |
| `llama3.2:3b` | 2GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Speed priority, English |
| `mistral:7b` | 4.1GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Strong reasoning, English |

### For Screenshot Analysis (Vision Capability Required)

| Model | Size | Speed | Quality | Recommended Use Case |
|-------|------|-------|---------|---------------------|
| `llava:7b` | 4.7GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | General vision understanding |
| `qwen2-vl:7b` | 4.7GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Strong Chinese OCR |
| `llava:13b` | 8GB | ⭐⭐ | ⭐⭐⭐⭐⭐ | High quality, more resources needed |

## Performance Optimization

### 1. GPU Acceleration

Ollama automatically uses available GPU (NVIDIA/Apple Silicon). Verify:

```bash
# Check if GPU is recognized
ollama ps

# View loaded models
ollama list
```

### 2. Concurrency Limits

Ollama processes one request by default, adjust via environment variables:

```bash
# Set concurrent requests
export OLLAMA_NUM_PARALLEL=2

# Set max loaded models
export OLLAMA_MAX_LOADED_MODELS=2

# Restart Ollama
ollama serve
```

### 3. Memory Management

```bash
# Set model unload time (seconds)
export OLLAMA_KEEP_ALIVE=5m

# Set context window size
# Control via max_tokens parameter in iDO
```

### 4. Adjust iDO Configuration

Edit `backend/config/config.toml`:

```toml
[processing]
# Reduce screenshot threshold to decrease images per LLM call
event_extraction_threshold = 30

# Increase processing interval to give Ollama more time
processing_interval = 60
```

## Troubleshooting

### 1. Connection Failed

**Symptom**: Test connection fails, cannot access

**Solution**:
```bash
# Check if Ollama is running
ps aux | grep ollama

# Check if port is open
curl http://localhost:11434/api/tags

# Restart Ollama
killall ollama
ollama serve
```

### 2. Model Not Found

**Symptom**: API returns "model not found"

**Solution**:
```bash
# List downloaded models
ollama list

# Ensure model name matches exactly (including tag)
# Correct: qwen2.5:7b
# Wrong: qwen2.5, qwen
```

### 3. Slow Response

**Symptom**: Event extraction takes too long

**Optimization**:
1. Use smaller model (e.g., `llama3.2:3b`)
2. Reduce screenshot count (adjust `event_extraction_threshold`)
3. Lower image resolution (adjust `compression_level = "ultra"`)
4. Enable GPU acceleration

### 4. Out of Memory

**Symptom**: Ollama crashes or system freezes

**Solution**:
```bash
# Use quantized version
ollama pull qwen2.5:7b-q4  # 4-bit quantization, half memory

# Or use smaller model
ollama pull qwen2.5:3b
```

## Multiple Model Switching

iDO supports configuring multiple models and quick switching:

```bash
# Download multiple models
ollama pull qwen2.5:7b
ollama pull llama3.2:3b
ollama pull mistral:7b

# Configure each model separately in iDO
# Switch active model anytime in settings
```

**Recommended Strategy**:
- **Day Work**: Use fast model (`llama3.2:3b`)
- **Evening Summary**: Switch to high-quality model (`qwen2.5:7b`)
- **Important Tasks**: Use cloud models (GPT-4, Claude)

## Comparison: Local vs Cloud

| Dimension | Ollama Local | Cloud API (GPT-4) |
|-----------|--------------|-------------------|
| **Privacy** | ⭐⭐⭐⭐⭐ Fully local | ⭐⭐ Data uploaded to cloud |
| **Cost** | ⭐⭐⭐⭐⭐ Completely free | ⭐⭐ Pay per token |
| **Speed** | ⭐⭐⭐ Hardware limited | ⭐⭐⭐⭐ Usually faster |
| **Quality** | ⭐⭐⭐⭐ 7B models | ⭐⭐⭐⭐⭐ Top-tier results |
| **Stability** | ⭐⭐⭐⭐ Depends on local | ⭐⭐⭐⭐ Depends on network |
| **Setup** | ⭐⭐⭐ Requires installation | ⭐⭐⭐⭐⭐ Ready to use |

## Advanced Configuration

### Custom Modelfile

Create optimized model configuration:

```bash
# Create Modelfile
cat > Modelfile << 'EOF'
FROM qwen2.5:7b

# Set system prompt
SYSTEM """You are an activity monitoring assistant focused on summarizing user work activities. Please describe what the user is doing in concise, professional language."""

# Set parameters
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 4096
EOF

# Create custom model
ollama create ido-qwen -f Modelfile

# Use in iDO
# Model name: ido-qwen
```

### Remote Ollama

Ollama can also run on remote servers:

```bash
# Server side (allow remote access)
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# iDO configuration
# API URL: http://192.168.1.100:11434/v1
```

## References

- [Ollama Official Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Ollama Model Library](https://ollama.com/library)
- [OpenAI API Compatibility](https://github.com/ollama/ollama/blob/main/docs/openai.md)
