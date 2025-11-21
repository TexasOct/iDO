# Ollama Quick Start (5-Minute Setup)

## Step 1: Install Ollama

```bash
# macOS
brew install ollama

# Or visit https://ollama.com/download
```

## Step 2: Download a Model

```bash
# Recommended: Qwen 2.5 7B (Bilingual, great quality)
ollama pull qwen2.5:7b

# Alternative: Llama 3.2 3B (Faster)
ollama pull llama3.2:3b
```

Download takes a few minutes, model size is ~4-5GB.

## Step 3: Configure in iDO

1. Open iDO → Settings → Model Management
2. Click "Add New Model"
3. Fill in configuration:

```
Configuration Name: Ollama Qwen
Provider: ollama
API URL: http://localhost:11434/v1
Model Name: qwen2.5:7b
API Key: ollama
Input Price: 0
Output Price: 0
```

4. Click "Test Connection" → Should see success message
5. Click "Save" → Click "Activate"

## Done!

iDO will now use your local Ollama model for analysis, completely free and privacy-safe.

## Common Issues

**Q: Connection failed?**
```bash
# Ensure Ollama is running
ollama serve
```

**Q: Model not found?**
```bash
# Check downloaded models
ollama list

# Ensure name matches exactly (including :7b suffix)
```

**Q: Too slow?**
```bash
# Use a smaller model
ollama pull llama3.2:3b

# In iDO, change model name to: llama3.2:3b
```

## Recommended Configurations

**Performance Priority** (Mac M1/M2/M3 or 16GB+ RAM):
```
Model: qwen2.5:7b
```

**Speed Priority** (8GB RAM or older devices):
```
Model: llama3.2:3b
```

**Maximum Privacy** (Fully offline):
```
Model: qwen2.5:7b
Network: Works even without internet connection
```
