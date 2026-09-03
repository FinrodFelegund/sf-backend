from enum import Enum
from functools import lru_cache

from openai import OpenAI

from chat.models import ChatSystemPrompt, Website
from shared.llm.citation import CITATION_INSTRUCTION
from storyfinder.settings import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    VIRTUAL_KEY,
)


class PromptType(Enum):
    CHAT = 'chat'
    SUMMARY = 'summary'
    GRAPH = 'graph'

class PromptLanguage(Enum):
    GER = 'ger'
    EN = 'eng'


class OpenAIClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model = OPENAI_MODEL
        self.base_url = OPENAI_BASE_URL
        self.api_key = OPENAI_API_KEY
        self.virtual_key = VIRTUAL_KEY
        self.client = self.init_client()
        self._initialized = True

    def init_client(self):
        if self.base_url:
            return OpenAI(base_url=self.base_url, api_key=self.api_key, default_headers={'x-bf-vk': self.virtual_key})
        else:
            return OpenAI(api_key=self.api_key)
    
    def get_active_prompt(self, prompt_type: PromptType, lang: PromptLanguage):
        prompt = ChatSystemPrompt.objects.filter(role=prompt_type.value, lang=lang.value).first()
        if not prompt:
            raise ValueError(f'No prompt for prompt type {prompt_type} and language {lang} found')
        return prompt.content

    def stream(self, messages: list[dict], model: str | None = None):
        model = model or self.model

        stream = self.client.chat.completions.create(model=model, messages=messages, stream=True)

        for chunk in stream:
            try:
                content = chunk.choices[0].delta.content

            except(AttributeError, IndexError):
                continue

            if content:
                yield content

    def build_chat_prompt(self, page_text: str, history_for_llm: list[dict], data: str):
        prompt = self.get_active_prompt(prompt_type=PromptType('chat'), lang=PromptLanguage('eng'))
        messages = [
            {'role': 'system', 'content': prompt.format(summary=page_text) + CITATION_INSTRUCTION}
        ]
        messages.extend({'role': m['role'], 'content': m['content']}
                for m in history_for_llm
                if m.get('role') and m.get('content'))
        messages.append({'role': 'user', 'content': data})
        return messages

    def response(self, messages: list[dict], model: str | None = None):
        model = model or self.model
        response = self.client.chat.completions.create(model=model, messages=messages)

        if response:
            return response.choices[0].message.content
        
    
    def build_summary_prompt(self, website: Website):
        prompt = self.get_active_prompt(prompt_type=PromptType('summary'), lang=PromptLanguage('eng'))
        messages = [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': website.content}]
        
        return messages

        
@lru_cache
def get_openai_client():
    return OpenAIClient()