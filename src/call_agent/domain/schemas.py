from fastapi import Form
from pydantic import BaseModel


class TwilioWebhookPayload(BaseModel):
    body: str
    from_number: str
    to_number: str
    message_sid: str

    @classmethod
    def from_form(
        cls,
        body: str = Form(alias="Body"),
        from_number: str = Form(alias="From"),
        to_number: str = Form(alias="To"),
        message_sid: str = Form(alias="MessageSid"),
    ) -> "TwilioWebhookPayload":
        return cls(
            body=body,
            from_number=from_number,
            to_number=to_number,
            message_sid=message_sid,
        )
