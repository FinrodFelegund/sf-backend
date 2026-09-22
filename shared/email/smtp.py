from django.core.mail import send_mail

from storyfinder import settings


def send_register_mail(email: str, code: list[int]):

    return
    
    code = ' '.join(code)
    send_mail(
        subject='Your storyfinder register code',
        message=f'Use this code to validate your registration\n{code}',
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )