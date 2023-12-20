import os

import openai

openai.api_base = "https://api.chatanywhere.tech/v1"


class ChatGPT:
    def __init__(self, apikey) -> None:
        openai.api_key = apikey

    def req(self, prompt):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            # model="gpt-4-8k",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        return response['choices'][0]['message']['content']


if __name__ == '__main__':
    apikey = "sk-dRElekBr6bZzh7OKyHQsCvq9yzV3OIAA6UJN0OqFu1YcygAZ"  # bzr
    llm = ChatGPT(apikey)
    prompt = """"
    
    """
    res = llm.req(prompt)
    print(res)
