"""Language checks for model-generated explanations, without changing trade data."""

import re


_CJK_IDEOGRAPHS = re.compile(
    r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF"
    r"\U00020000-\U0002FA1F\U00030000-\U000323AF]"
)


def contains_chinese(text: str) -> bool:
    """Detect CJK ideographs while allowing English Unicode punctuation."""
    return _CJK_IDEOGRAPHS.search(text) is not None
