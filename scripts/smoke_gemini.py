import os

import litellm

assert os.getenv("GEMINI_API_KEY"), "GEMINI_API_KEY no está en el entorno"

r = litellm.completion(
    model="gemini/gemini-2.5-flash",
    messages=[{"role": "user", "content": "ping"}],
)
print("OK:", r.choices[0].message.content)
