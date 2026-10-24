"""
Latin Dhivehi (Romanized Dhivehi) transliteration and language detection engine.

Converts Romanized Dhivehi (widely used in SMS, Telegram channels, and Sun Latin feeds)
into standard Thaana script with proper vowel diacritics (fili) and sukun.
Also provides accurate detection to distinguish Latin Dhivehi from English text.
"""
from __future__ import annotations

import re
from typing import Optional

# Unicode Thaana constants
THAANA_ALIFU = "\u0787"  # އ
SUKUN = "\u07B0"         # ް
ABAFILI = "\u07A6"       # ަ
AABAAFILI = "\u07A7"     # ާ
IBIFILI = "\u07A8"       # ި
EEBEEFILI = "\u07A9"     # ީ
UBUFILI = "\u07AA"       # ު
OOBOOFILI = "\u07AB"     # ޫ
EBEFILI = "\u07AC"       # ެ
EYBEYFILI = "\u07AD"     # ޭ
OBOFILI = "\u07AE"       # ޮ
OOBOAFILI = "\u07AF"     # ޯ

# High-frequency Latin Dhivehi vocabulary for instant canonical resolution
COMMON_LATIN_DHIVEHI_WORDS: dict[str, str] = {
    "gai": "ގައި",
    "ge": "ގެ",
    "ah": "އަށް",
    "ves": "ވެސް",
    "eh": "އެއް",
    "thah": "ތައް",
    "vefa": "ވެފައި",
    "vanee": "ވަނީ",
    "kuranee": "ކުރަނީ",
    "koffai": "ކޮށްފައި",
    "kuri": "ކުރި",
    "kuran": "ކުރަން",
    "kurin": "ކުރިން",
    "meehun": "މީހުން",
    "meehunnah": "މީހުންނަށް",
    "meehakah": "މީހަކަށް",
    "meehaku": "މީހަކު",
    "meehunge": "މީހުންގެ",
    "ekaku": "އެކަކު",
    "raajje": "ރާއްޖެ",
    "raajjeygai": "ރާއްޖޭގައި",
    "raajjeyge": "ރާއްޖޭގެ",
    "sarukaaru": "ސަރުކާރު",
    "sarukaarun": "ސަރުކާރުން",
    "majilis": "މަޖިލިސް",
    "majilisa": "މަޖިލީހަށް",
    "majilisah": "މަޖިލީހަށް",
    "police": "ފުލުހުން",
    "masala": "މައްސަލަ",
    "kamah": "ކަމަށް",
    "kameh": "ކަމެއް",
    "accident": "އެކްސިޑެންޓް",
    "dhanee": "ދަނީ",
    "hure": "ހުރެ",
    "dhey": "ދޭ",
    "ithuru": "އިތުރު",
    "nuvatha": "ނުވަތަ",
    "nubai": "ނުބައި",
    "hama": "ހަމަ",
    "emme": "އެންމެ",
    "dheke": "ދެކެ",
    "libey": "ލިބޭ",
    "libi": "ލިބި",
    "kandhaalhai": "ކަނޑައަޅައި",
    "falhu": "ފަޅު",
    "dhookoh": "ދޫކޮށް",
    "bunan": "ބުނަން",
    "rayyithun": "ރައްޔިތުން",
    "rayyithunge": "ރައްޔިތުންގެ",
    "soelaha": "ސޯލިހު",
    "muizzu": "މުޢިއްޒު",
    "president": "ރައީސް",
    "anhenun": "އަންހެނުން",
    "firihenun": "ފިރިހެނުން",
    "male": "މާލެ",
    "hulhumale": "ހުޅުމާލެ",
    "fuvahmulah": "ފުވައްމުލައް",
    "addu": "އައްޑޫ",
    "hospital": "ހޮސްޕިޓަލް",
    "ventilator": "ވެންޓިލޭޓަރު",
    "serious": "ސީރިއަސް",
    "aniyaavi": "އަނިޔާވި",
    "hingi": "ހިނގި",
    "hinguvi": "ހިންގި",
    "maruvi": "މަރުވި",
    "haalu": "ޙާލު",
    "fuhpathuge": "ފުއްޕާމޭގެ",
    "balithah": "ބަލިތައް",
    "ithuruvanee": "އިތުރުވަނީ",
    "dhuniye": "ދުނިޔެ",
    "faiysa": "ފައިސާ",
    "hiya": "ހިޔާ",
    "dhen": "ދެން",
    "noon": "ނޫން",
    "ethi": "އެތި",
    "viyyaa": "ވިއްޔާ",
    "hukuru": "ހުކުރު",
    "dhuvas": "ދުވަސް",
}

# Digraph consonants (must match before single letter consonants)
DIGRAPH_CONSONANTS: list[tuple[str, str]] = [
    ("sh", "\u0781"),   # ށ
    ("lh", "\u0785"),   # ޅ
    ("dh", "\u078B"),   # ދ
    ("th", "\u078C"),   # ތ
    ("gn", "\u078F"),   # ޏ
    ("ny", "\u078F"),   # ޏ
    ("ch", "\u0797"),   # ޗ
    ("kh", "\u0799"),   # ޚ
    ("gh", "\u079F"),   # ޣ
]

SINGLE_CONSONANTS: dict[str, str] = {
    "h": "\u0780",  # ހ
    "n": "\u0782",  # ނ
    "r": "\u0783",  # ރ
    "b": "\u0784",  # ބ
    "k": "\u0786",  # ކ
    "v": "\u0788",  # ވ
    "w": "\u0788",  # ވ
    "m": "\u0789",  # މ
    "f": "\u078A",  # ފ
    "l": "\u078D",  # ލ
    "g": "\u078E",  # ގ
    "s": "\u0790",  # ސ
    "d": "\u0791",  # ޑ
    "z": "\u0792",  # ޒ
    "t": "\u0793",  # ޓ
    "y": "\u0794",  # ޔ
    "p": "\u0795",  # ޕ
    "j": "\u0796",  # ޖ
    "q": "\u07A0",  # ޤ
    "c": "\u0797",  # ޗ
    "x": "\u0790",  # ސ
}

VOWEL_PATTERNS: list[tuple[str, str]] = [
    ("aabaa", AABAAFILI),
    ("aa", AABAAFILI),
    ("ee", EEBEEFILI),
    ("eey", EEBEEFILI),
    ("iy", EEBEEFILI),
    ("oo", OOBOOFILI),
    ("uu", OOBOOFILI),
    ("ey", EYBEYFILI),
    ("ei", EYBEYFILI),
    ("oa", OOBOAFILI),
    ("a", ABAFILI),
    ("i", IBIFILI),
    ("u", UBUFILI),
    ("e", EBEFILI),
    ("o", OBOFILI),
]

# Grammatical and lexical markers unique to Dhivehi in Latin script
DHIVEHI_ONLY_LATIN_WORDS: set[str] = {
    "gai", "ge", "ah", "ves", "eh", "thah", "vefa", "vanee", "kuranee",
    "koffai", "kuri", "kuran", "kurin", "meehun", "meehakah", "meehaku",
    "meehunge", "meehunnah", "ekaku", "raajjeygai", "raajjeyge", "sarukaarun",
    "sarukaaru", "majilisa", "majilisah", "masala", "kamah", "kameh", "dhanee",
    "hure", "dhey", "ithuru", "nuvatha", "nubai", "hama", "emme", "dheke",
    "libey", "libi", "kandhaalhai", "falhu", "dhookoh", "bunan", "rayyithun",
    "rayyithunge", "anhenun", "firihenun", "fuvahmulah", "addu", "aniyaavi",
    "hingi", "hinguvi", "maruvi", "haalu", "fuhpathuge", "balithah", "ithuruvanee",
    "dhuniye", "faiysa", "hiya", "dhen", "noon", "ethi", "viyyaa", "hukuru",
    "dhuvas", "kudakujjaa", "kudakudhin", "dhekunu", "uthuru", "fiyavalhu",
    "soelaha", "kandafalhu", "dhonbandharu", "vaarey"
}

ENGLISH_COMMON_WORDS: set[str] = {
    "the", "and", "is", "are", "was", "were", "of", "to", "in", "for",
    "with", "from", "by", "on", "at", "after", "returns", "announces",
    "official", "officials", "state", "visit", "agreement", "project",
    "cabinet", "signed", "police", "investigating", "president", "minister",
    "ministry", "development", "national", "public", "launched", "says"
}


def is_latin_dhivehi(text: str) -> bool:
    """
    Determine if a piece of text is written in Latin Dhivehi (Romanized Dhivehi)
    rather than standard English.
    """
    if not text or len(text.strip()) < 5:
        return False

    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = cleaned.split()
    if not words:
        return False

    # Check for Dhivehi stop words vs English words
    dhivehi_matches = sum(1 for w in words if w in DHIVEHI_ONLY_LATIN_WORDS)
    english_matches = sum(1 for w in words if w in ENGLISH_COMMON_WORDS)

    # Strong markers that unambiguously mean Dhivehi syntax
    strong_markers = {
        "gai", "vanee", "vefa", "kuranee", "koffai", "meehun", "meehakah",
        "meehaku", "meehunnah", "raajjeygai", "kandhaalhai", "ithuruvanee",
        "fuhpathuge", "balithah", "aniyaavi", "sarukaarun", "majilisah",
        "rayyithunge", "hinguvi", "maruvi"
    }
    has_strong_marker = any(w in strong_markers for w in words)

    if has_strong_marker and dhivehi_matches >= 1:
        return True

    # If Dhivehi markers outnumber English words and there are at least 2 Dhivehi markers
    if dhivehi_matches >= 2 and dhivehi_matches > english_matches:
        return True

    return False


def _transliterate_word(word: str) -> str:
    """Transliterate a single Latin Dhivehi token to Thaana."""
    word_low = word.lower().strip()
    if not word_low:
        return ""

    # Check dictionary first for 100% natural spelling
    if word_low in COMMON_LATIN_DHIVEHI_WORDS:
        return COMMON_LATIN_DHIVEHI_WORDS[word_low]

    # Special handling for common word endings in Dhivehi:
    # '...gai' -> '...ގައި'
    if len(word_low) > 3 and word_low.endswith("gai"):
        stem = word_low[:-3]
        return _transliterate_word(stem) + "ގައި"
    # '...thah' -> '...ތައް'
    if len(word_low) > 4 and word_low.endswith("thah"):
        stem = word_low[:-4]
        return _transliterate_word(stem) + "ތައް"
    # '...eh' -> '...ެއް'
    if len(word_low) > 2 and word_low.endswith("eh") and not word_low.endswith("yeh"):
        stem = word_low[:-2]
        return _transliterate_word(stem) + "ެއް"
    # '...ah' -> '...ަށް'
    if len(word_low) > 2 and word_low.endswith("ah"):
        stem = word_low[:-2]
        return _transliterate_word(stem) + "ަށް"

    # Phonetic character-by-character parsing
    i = 0
    n = len(word_low)
    res: list[str] = []

    while i < n:
        char = word_low[i]

        # Non-alphabetic passthrough
        if not char.isalpha():
            res.append(char)
            i += 1
            continue

        # Check if current position matches a vowel without preceding consonant (syllable start)
        is_initial = (i == 0 or word_low[i - 1] in " \t-/:")
        prev_was_vowel = (i > 0 and word_low[i - 1] in "aeiouy")

        # 1. Match Consonant
        matched_consonant = None
        consonant_len = 0

        # Try digraphs first (sh, lh, dh, th, gn, ny, ch, kh, gh)
        if i + 1 < n:
            two = word_low[i:i + 2]
            for dg, th_char in DIGRAPH_CONSONANTS:
                if two == dg:
                    matched_consonant = th_char
                    consonant_len = 2
                    break

        # Single consonant
        if not matched_consonant and char in SINGLE_CONSONANTS:
            matched_consonant = SINGLE_CONSONANTS[char]
            consonant_len = 1

        if matched_consonant:
            i += consonant_len
            # Look ahead for vowel attached to this consonant
            matched_vowel = None
            vowel_len = 0
            for v_str, v_fili in VOWEL_PATTERNS:
                if word_low.startswith(v_str, i):
                    matched_vowel = v_fili
                    vowel_len = len(v_str)
                    break

            if matched_vowel:
                res.append(matched_consonant + matched_vowel)
                i += vowel_len
            else:
                # Consonant with no following vowel gets Sukun
                res.append(matched_consonant + SUKUN)
        else:
            # Position starts with vowel (e.g. at start of word or diphthong): uses Alifu carrier
            matched_vowel = None
            vowel_len = 0
            for v_str, v_fili in VOWEL_PATTERNS:
                if word_low.startswith(v_str, i):
                    matched_vowel = v_fili
                    vowel_len = len(v_str)
                    break

            if matched_vowel:
                res.append(THAANA_ALIFU + matched_vowel)
                i += vowel_len
            else:
                # Passthrough unknown letter
                res.append(char)
                i += 1

    return "".join(res)


def transliterate_latin_to_thaana(text: str) -> str:
    """
    Transliterate Latin Dhivehi text into Thaana script, preserving punctuation and numbers.
    """
    if not text:
        return text

    # Split while preserving delimiters (spaces, punctuation)
    tokens = re.split(r"(\s+|[.,!?:;\"'()\[\]{}—–\-])", text)
    converted: list[str] = []

    for token in tokens:
        if not token:
            continue
        # If token has letters, transliterate word
        if re.search(r"[a-zA-Z]", token):
            converted.append(_transliterate_word(token))
        else:
            converted.append(token)

    return "".join(converted)
