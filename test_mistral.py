import os

from dotenv import load_dotenv
from mistralai.client import Mistral


load_dotenv()


api_key = os.environ["MISTRAL_API_KEY"]
model = os.environ["MISTRAL_MODEL"]


client = Mistral(
    api_key=api_key
)


response = client.chat.complete(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "Say hello in one short sentence.",
        }
    ],
)


print(
    response.choices[0].message.content
)
