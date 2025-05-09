from llama_cpp import Llama

# Caminho para o modelo .gguf
model_path = "llama.cpp/models/llama-2-7b/llama-2-7b.Q4_K_M.gguf"

# Inicializa o modelo com configuração segura
llm = Llama(model_path=model_path, n_ctx=512, n_threads=4)

# Prompt simples
prompt = "Explique brevemente o que é justiça."

# Geração da resposta
output = llm(prompt, max_tokens=50)

# Exibe a resposta
print("✅ Resposta:")
print(output["choices"][0]["text"].strip())

