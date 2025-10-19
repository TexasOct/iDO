# ⭐ Just use `commands` as usual
async def greeting(name: str) -> str:
    """A simple command that returns a greeting message.

    @param name - The name of the person to greet.
    """
    # 👆 This pydoc will be converted to tsdoc
    return f"Hello, {name}!"