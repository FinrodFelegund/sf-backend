from django.db import transaction
from chat.models import ChatSystemPrompt
#from graph.models import *
from storyfinder.settings import SYSTEM_DATA_DIR
from pathlib import Path
import json

class SystemPromptSetupService:
    def __init__(self):
        self.combinations = self.combine(['ger', 'eng'], ['chat', 'summary', 'graph'])

    def combine(self, languages, promtp_types):
        out = []

        for lang in languages:
            for prompt_type in promtp_types:
                out.append((lang, prompt_type))

        return out


    @transaction.atomic
    def reset_dev_environment(self):
        ChatSystemPrompt.objects.all().delete()

    @transaction.atomic
    def setup_dev_environment(self):
        promptpath = Path(SYSTEM_DATA_DIR) / 'prompts' / 'systemprompt.json'

        with open(promptpath, mode='r') as f:
            json_file = json.load(f)

            for l, t in self.combinations:
                prompt = json_file[l][t]
                prompt = ChatSystemPrompt.objects.create(
                    name=f'Prompt for {t} in language {l}',
                    content=prompt,
                    role=t,
                    lang=l
                )

        return len(self.combinations)

