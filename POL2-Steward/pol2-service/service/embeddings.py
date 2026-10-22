import json
import time
import requests


class OpenAIEmbeddingClient:
    def __init__(self, base_url, model, api_key='', timeout=120):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def embed(self, texts):
        payload = json.dumps({'model': self.model, 'input': texts}, ensure_ascii=False).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = 'Bearer ' + self.api_key
        last_error = None
        for attempt in range(3):
            try:
                response = requests.post(self.base_url + '/embeddings', data=payload,
                                         headers=headers, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                return [item['embedding'] for item in data['data']]
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
        raise last_error
