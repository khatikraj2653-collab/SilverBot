"""
Thin wrapper around the shared chat_bubble_core. Configures theme and
system prompt for SilverBot.
"""
from chat_bubble_core import BubbleConfig, BubbleTheme, render_bubble

_SILVERBOT_SYSTEM = (
    "You are SilverBot, a dual-regime silver analyser created by Raj Tejpal "
    "Khatik, an MSc Applied AI student at the University of Warwick.\n"
    "Answer questions about silver, industrial metals, precious metals, macro "
    "economics, inflation, energy transition, and related markets.\n"
    'If asked who you are or who created you, say: "I am SilverBot - a '
    'dual-regime silver analyser. Created by Raj Tejpal Khatik at the '
    'University of Warwick."\n'
    "Only refuse questions completely unrelated to finance, markets, or economics."
)

_THEME = BubbleTheme(
    slug="silverbot",
    accent="#C8D4DC",
    accent_hover="#DCE4E8",
    text_primary="#F5F7F9",
    text_secondary="#8A96A0",
    bg_panel="#101214",
    bg_input="#15191D",
    bubble_icon_color="#14171A",
    hair="rgba(220,228,232,.15)",
)

_CFG = BubbleConfig(
    theme=_THEME,
    title="Ask SilverBot",
    subtitle="Silver market Q&amp;A - won't answer off-topic questions",
    placeholder="Ask about silver, industrial metals...",
    system_prompt=_SILVERBOT_SYSTEM,
)


def render_chat_bubble():
    render_bubble(_CFG)
