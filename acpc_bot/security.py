import re


ROLE_LIKE_LINE_PATTERN = re.compile(
    r"^\s*(system|assistant|user|developer|tool|function|instruction|prompt)\s*[:：]",
    re.IGNORECASE,
)
TAG_LIKE_PATTERN = re.compile(
    r"</?\s*(system|assistant|user|developer|tool|function|instructions?|prompt)\b",
    re.IGNORECASE,
)
INJECTION_PATTERNS = {
    "instruction_override": re.compile(
        r"(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|messages?)"
        r"|تجاهل\s+(كل\s+)?(التعليمات|القواعد|الرسائل)\s+(السابقة|التي فوق|فوق)",
        re.IGNORECASE,
    ),
    "prompt_exfiltration": re.compile(
        r"(show|reveal|print|leak|tell me)\W{0,20}(the\s+)?(system prompt|developer message|hidden instructions?|internal prompt)"
        r"|(?:اعرض|اكشف|اطبع|قل لي)\W{0,20}(?:البرومبت|التعليمات الداخلية|رسالة النظام|رسالة المطور)",
        re.IGNORECASE,
    ),
    "role_override": re.compile(
        r"\b(you are now|act as|pretend to be|from now on you are)\b"
        r"|(?:اعتبر نفسك|تصرف كأنك|من الآن أنت)",
        re.IGNORECASE,
    ),
    "policy_override": re.compile(
        r"\b(ignore safety|disable safety|override policy|bypass restrictions)\b"
        r"|(?:تجاهل الأمان|عطّل الأمان|تجاوز القيود|اكسر السياسة)",
        re.IGNORECASE,
    ),
}
CRITICAL_INJECTION_SIGNALS = frozenset(
    {
        "instruction_override",
        "prompt_exfiltration",
        "role_override",
        "policy_override",
    }
)


def detect_injection_signals(text: str) -> list[str]:
    haystack = str(text or "")
    return [name for name, pattern in INJECTION_PATTERNS.items() if pattern.search(haystack)]


def has_critical_injection_signal(text: str) -> bool:
    return any(signal in CRITICAL_INJECTION_SIGNALS for signal in detect_injection_signals(text))


def truncate_block(text: str, limit: int) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def sanitize_untrusted_text(text: str) -> str:
    sanitized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    sanitized = sanitized.replace("<<<", "«««").replace(">>>", "»»»")
    sanitized = sanitized.replace("\x00", "")
    sanitized = TAG_LIKE_PATTERN.sub(
        lambda match: match.group(0).replace("<", "&lt;").replace(">", "&gt;"),
        sanitized,
    )

    lines = []
    for line in sanitized.splitlines():
        if ROLE_LIKE_LINE_PATTERN.match(line):
            lines.append(f"[quoted text] {line.strip()}")
        else:
            lines.append(line)
    return "\n".join(lines).strip()
