import re
from typing import Dict, List

# 'key:"value"' または 'key:value' 形式のパターンと、独立した単語を見つけるための正規表現
QUERY_REGEX = re.compile(r'(\w+):"([^"]+)"|(\w+):(\S+)|"([^"]+)"|(\S+)')


def parse_query(query_str: str) -> Dict[str, List[str]]:
    """Parse a search query string into a structured dictionary.

    Args:
        query_str: The raw search query string.

    Returns:
        A dictionary with keys like 'name', 'desc', 'tag', 'term'.
        Each key contains a list of parsed values.

    """
    parsed: Dict[str, List[str]] = {
        "name": [],
        "desc": [],
        "tag": [],
        "term": [],
    }

    if not query_str:
        return parsed

    matches = QUERY_REGEX.finditer(query_str)
    for match in matches:
        # key:"value"
        if match.group(1) and match.group(2):
            key = match.group(1).lower()
            value = match.group(2).strip()
            if key in parsed:
                parsed[key].append(value)
        # key:value
        elif match.group(3) and match.group(4):
            key = match.group(3).lower()
            value = match.group(4).strip()
            if key in parsed:
                parsed[key].append(value)
        # "value"
        elif match.group(5):
            parsed["term"].append(match.group(5).strip())
        # value
        elif match.group(6):
            parsed["term"].append(match.group(6).strip())

    return parsed
