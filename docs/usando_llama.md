# 🦙 Usando LLaMA Localmente com CPU

Este pacote permite instalar e rodar o modelo LLaMA (ou similar) localmente em máquinas **sem GPU**, utilizando o `llama.cpp` com modelos quantizados (formato GGUF).

## 🛠️ Instalação manual

```bash
chmod +x instalar_llama_local.sh
./instalar_llama_local.sh
```

## 🐳 Docker

### Build

```bash
docker build -t llama-local .
```

### Execução

```bash
docker run --rm -it \
  -v $(pwd)/modelos:/app/llama.cpp/models/llama-2-7b \
  llama-local
```

## 📥 Modelo

Baixe manualmente de: https://huggingface.co/TheBloke/Llama-2-7B-GGUF
Use o arquivo `Llama-2-7B-Q4_K_M.gguf` e coloque-o na pasta `modelos`.

---
FGV - Teste do modelo LLaMA sem GPU
