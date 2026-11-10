"""Free best-vs-worst comparison: no API key, no per-call cost.

Public numbers plus what the title and description say (offer, call to action, hook style,
link). Nothing here watches the video itself; transcripts arrive in Step 4. Reading comments
with the Laya model happens on the GPU machine through the task queue (api/v1/tasks.py).
"""
import re

from ada.spi.comparer import AdEvidence, Comparison, Difference
from ada.spi.video_metadata import VideoMeta

# English plus common Hinglish; matched case-insensitively against title + description
_OFFER = re.compile(
    r"(flat )?\d+\s?% ?off|flat (rs\.? ?|₹\s?)?\d[\d,]*( off)?|₹\s?\d[\d,]*|rs\.? ?\d[\d,]*|free (trial|delivery|shipping|class)|"
    r"\b(discount|cashback|coupon|promo code|use code|sale|deal|offer|buy \d get \d|bogo)\b|"
    r"limited time|\bfree\b", re.IGNORECASE)
_CTA = re.compile(
    r"\b(shop now|buy now|order now|book now|download|install|sign up|register|join( now)?|"
    r"subscribe|visit|click|call (now|us)|try (it )?(now|free|today)|get started|"
    r"link in (the )?(bio|description)|abhi (order|kharid\w*|download)|order kar\w*)\b",
    re.IGNORECASE)
_LINK = re.compile(r"https?://|www\.", re.IGNORECASE)



def _times(a: float, b: float) -> str:
    if not b:
        return "far more" if a else "the same"
    r = a / b
    return f"{r:.1f}x" if r < 10 else f"{r:.0f}x"


def _secs(s: int) -> str:
    return f"{s // 60}m {s % 60}s" if s >= 60 else f"{s}s"


def _found(pattern: re.Pattern, v: VideoMeta) -> str:
    """First match in the title, else the description, as the viewer would read it."""
    m = pattern.search(v.title) or pattern.search(v.description)
    return m.group(0).strip() if m else ""


def _title_hook(title: str) -> str:
    if "?" in title:
        return "Asks a question"
    if re.search(r"\bhow to\b|\bhow i\b", title, re.IGNORECASE):
        return "How-to"
    if re.search(r"\d", title):
        return "Uses a number"
    letters = [c for c in title if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        return "All caps"
    return "Plain statement"


class RulesComparer:
    async def compare(self, best: AdEvidence, worst: AdEvidence, query: str) -> Comparison:
        b, w = best.video, worst.video

        strengths, weaknesses, tips = [], [], []
        offer_b, offer_w = _found(_OFFER, b), _found(_OFFER, w)
        cta_b, cta_w = _found(_CTA, b), _found(_CTA, w)
        link_b, link_w = bool(_LINK.search(b.description)), bool(_LINK.search(w.description))
        diffs = [
            Difference(aspect="Views per day", best=f"{best.views_per_day:,.0f}",
                       worst=f"{worst.views_per_day:,.0f}",
                       why_it_matters="Daily reach, so an older ad doesn't win just by being old."),
            Difference(aspect="Engagement", best=f"{best.engagement_rate:.2%}",
                       worst=f"{worst.engagement_rate:.2%}",
                       why_it_matters="(Likes + comments) ÷ views: how many viewers reacted."),
            Difference(aspect="Length", best=_secs(b.duration_seconds),
                       worst=_secs(w.duration_seconds),
                       why_it_matters="Shorter ads are watched to the end more often."),
            Difference(aspect="Offer", best=offer_b or "None found", worst=offer_w or "None found",
                       why_it_matters="A clear deal gives viewers a reason to act now."),
            Difference(aspect="Call to action", best=cta_b or "None found",
                       worst=cta_w or "None found",
                       why_it_matters="Viewers act more often when told exactly what to do."),
            Difference(aspect="Title", best=_title_hook(b.title), worst=_title_hook(w.title),
                       why_it_matters="The title and thumbnail decide whether people click."),
        ]

        if offer_b and not offer_w:
            strengths.append(f"Makes a clear offer: “{offer_b}”.")
            weaknesses.append("No offer or deal in the title or description.")
            tips.append("Put one clear offer in the title or first line of the description.")
        if cta_b and not cta_w:
            strengths.append(f"Tells viewers what to do: “{cta_b}”.")
            weaknesses.append("Doesn't tell viewers what to do next.")
            tips.append("End with one direct call to action, like “Shop now” or “Start free”.")
        if link_b and not link_w:
            weaknesses.append("No link in the description, so interested viewers can't act.")
            tips.append("Add your landing-page link at the top of the description.")
        if b.duration_seconds and w.duration_seconds and b.duration_seconds < w.duration_seconds:
            strengths.append(f"Shorter: {_secs(b.duration_seconds)} vs "
                             f"{_secs(w.duration_seconds)}.")
            tips.append(f"Try keeping your ad close to {_secs(b.duration_seconds)}.")
        if worst.comments is None and best.comments is not None:
            weaknesses.append("Comments are turned off, which hides feedback and social proof.")
        tips.append("Open both videos and compare the first 5 seconds: the hook decides most views.")

        caveat = "Based on public numbers and the title and description, not the video itself."
        return Comparison(
            headline=f"“{b.title}” got {_times(best.views_per_day, worst.views_per_day)} the daily "
                     f"views and {_times(best.engagement_rate, worst.engagement_rate)} the "
                     f"engagement of “{w.title}”.",
            best_strengths=strengths, worst_weaknesses=weaknesses, differences=diffs,
            recommendations=list(dict.fromkeys(tips)), caveat=caveat,
            analysed_by="rules")
