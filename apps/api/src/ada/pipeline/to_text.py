"""Step 2: build ONE text document per ad from every available signal."""


def build_text_doc(title: str, description: str, transcript: str | None,
                   ocr: str | None, frames: str | None, landing: str | None) -> str:
    parts = [("TITLE", title), ("DESCRIPTION", description), ("SPEECH", transcript),
             ("ON-SCREEN TEXT", ocr), ("VISUALS", frames), ("LANDING PAGE", landing)]
    return "\n\n".join(f"[{k}]\n{v}" for k, v in parts if v)
