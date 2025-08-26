import requests


def chat_with_model(token):
    url = 'http://20.98.105.56:3000/api/chat/completions'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = {
        "model": "rns96/deepseek-R1-ablated:f16_Q4KM",
        "messages": [
            {
                "role": "user",
                "content": "Resuma a noticia https://edition.cnn.com/2025/06/11/politics/trump-military-los-angeles-protests-fort-bragg"}
        ],
        "temperature": 0.4,
    }

    response = requests.post(url, headers=headers, json=data)

    # Verifica se a solicitação foi bem-sucedida
    if response.status_code == 200:
        return response.json()  # Retorna os dados da resposta em formato JSON
    else:
        print(f"Erro na solicitação: {response.status_code}")
        print(response.text)
        return None


if __name__ == "__main__":
    # Chama a função e obtém a saída
    chat_response = chat_with_model('sk-069c9cad6142478aa2e11aa5f6bca919')

    # Imprime o resultado
    print(chat_response)