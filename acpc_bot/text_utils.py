import re


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_+#]+|[\u0600-\u06FF]+")
CODE_FENCE_PATTERN = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "do",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "please",
    "so",
    "that",
    "the",
    "this",
    "to",
    "we",
    "what",
    "why",
    "with",
    "you",
    "your",
    "في",
    "من",
    "على",
    "عن",
    "الى",
    "إلى",
    "او",
    "أو",
    "و",
    "يا",
    "هل",
    "هو",
    "هي",
    "اذا",
    "إذا",
    "شو",
    "كيف",
    "ليش",
    "انا",
    "أنا",
    "انت",
    "أنت",
    "مع",
    "بدنا",
    "بدي",
}

TAXONOMY_KEYWORDS = {
    "Frequency Arrays/Sets": [
        "frequency",
        "count",
        "counts",
        "set",
        "unordered_set",
        "map",
        "unordered_map",
        "pangram",
        "duplicate",
        "distinct",
        "letters",
        "characters",
        "char",
        "histogram",
        "تكرار",
        "عد",
        "حروف",
        "محارف",
    ],
    "Binary Search/Logarithms": [
        "binary search",
        "lower_bound",
        "upper_bound",
        "search on answer",
        "mid",
        "monotonic",
        "log",
        "logarithm",
        "log2",
        "bounds",
        "ثنائي",
        "لوغاريتم",
    ],
    "Graph Theory": [
        "graph",
        "graphs",
        "node",
        "nodes",
        "edge",
        "edges",
        "tree",
        "bfs",
        "dfs",
        "dijkstra",
        "shortest path",
        "adjacency",
        "traversal",
        "connected",
        "cycle",
        "graph theory",
        "رسم",
        "عقدة",
        "حواف",
        "مسار",
    ],
    "Dynamic Programming": [
        "dp",
        "dynamic programming",
        "memo",
        "memoization",
        "tabulation",
        "state",
        "states",
        "transition",
        "knapsack",
        "ribbon",
        "ديناميك",
    ],
    "Two Pointers / Prefix Sum": [
        "two pointers",
        "two pointer",
        "sliding window",
        "prefix",
        "prefix sum",
        "subarray",
        "window",
        "runner",
        "pointer",
        "مؤشرين",
        "بادئة",
    ],
}


def normalize_space(text: str) -> str:
    return " ".join(str(text or "").split())


def truncate_text(text: str, limit: int) -> str:
    text = normalize_space(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(str(text or "").lower())]
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def detect_taxonomy(text: str) -> list[str]:
    haystack = str(text or "").lower()
    matched = []
    for label, keywords in TAXONOMY_KEYWORDS.items():
        if any(keyword.lower() in haystack for keyword in keywords):
            matched.append(label)
    return matched


def looks_like_code(text: str) -> bool:
    if CODE_FENCE_PATTERN.search(text):
        return True
    line_count = len(text.splitlines())
    signal = sum(text.count(char) for char in "{};#<>[]()")
    return line_count >= 4 and signal >= 5


def extract_code_snippet(text: str) -> str:
    blocks = [block.strip() for block in CODE_FENCE_PATTERN.findall(text) if block.strip()]
    if blocks:
        return "\n\n".join(blocks)
    if looks_like_code(text):
        return text.strip()
    return ""


def add_line_numbers(code: str) -> str:
    return "\n".join(f"{index + 1}: {line}" for index, line in enumerate(code.splitlines()))


def split_long_message(text: str, limit: int) -> list[str]:
    text = str(text or "").strip()
    if not text:
        return ["Empty response."]

    parts = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1 or split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at == -1 or split_at < limit // 2:
            split_at = limit
        parts.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    if remaining:
        parts.append(remaining)

    return parts
