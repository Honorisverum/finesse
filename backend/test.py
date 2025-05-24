import re


def split_opening_text(text) -> tuple[str, str]:
    """
    Splits opening text into roleplay text (enclosed in asterisks) and regular text.
    Returns a list [roleplay_text, regular_text] where roleplay_text includes the asterisks.
    """
    roleplay_match = re.search(r'(\*[^*]*\*)', text)
    if not roleplay_match:
        return '', text.strip()
    roleplay_text = roleplay_match.group(1)
    regular_text = text.replace(roleplay_text, '', 1).strip()
    return roleplay_text, regular_text


print(split_opening_text("I'm fine, thank you!"))