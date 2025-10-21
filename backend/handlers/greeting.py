# ⭐ Universal API handler supporting PyTauri and FastAPI
from . import api_handler
from models import Person

@api_handler(body=Person, method="POST", path="/greeting", tags=["demo"])
async def greeting(body: Person) -> str:
    """A simple command that returns a greeting message.

    @param body - The person to greet.
    """
    # 👆 This pydoc will be converted to tsdoc
    return f"Hello, {body.name}!"