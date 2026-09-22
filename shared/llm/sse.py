import json

DONE = 'data: [DONE]\n\n'

def frame(payload: dict) -> str:
    return f'data: {json.dumps(payload)}\n\n'

def error_frame(message: str, code: str = 'stream_failed') -> str:
    return frame({'error': message, 'code': code})