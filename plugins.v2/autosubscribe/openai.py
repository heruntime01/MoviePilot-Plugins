import time
import requests
from app.log import logger

class OpenAiClient:
    def __init__(self, api_key: str, proxy: str = None):
        self.api_key = api_key
        self.proxy = proxy
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }

    def chat_completion(self, message: str) -> str:
        """
        调用 ChatGPT API
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": message}],
            "temperature": 0.7
        }
        
        try:
            response = self.session.post(url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                logger.error(f"API 调用失败: {response.text}")
                return None
        except Exception as e:
            logger.error(f"API 请求异常: {str(e)}")
            return None 