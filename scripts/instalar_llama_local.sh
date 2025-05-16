#!/bin/bash

# Atualiza e instala dependências
sudo apt update && sudo apt install -y build-essential cmake git curl wget unzip git-lfs python3-pip

# Instala o git-lfs necessário para Hugging Face
git lfs install

# Clona o repositório llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j$(nproc)

# Cria pasta de modelos
mkdir -p models/llama-2-7b
cd models/llama-2-7b

# Aviso de download manual
echo "Atenção: baixe manualmente o modelo GGUF de https://huggingface.co/TheBloke/Llama-2-7B-GGUF e salve aqui."
echo "Sugestão: use o modelo Llama-2-7B-Q4_K_M.gguf para uso em CPU."

cd ../..

echo "✅ Instalação concluída. Para testar, use:"
echo "./main -m models/llama-2-7b/Llama-2-7B-Q4_K_M.gguf -p 'Teste de execução local do modelo LLaMA'"
