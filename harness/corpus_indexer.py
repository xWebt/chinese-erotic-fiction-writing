"""Corpus indexer: scan, filter, score, and index the novel corpus.

Walks the corpus directory, auto-detects encoding (GBK/UTF-8), splits into
passages, applies hard filters, scores technique density, and stores results
in a SQLite database for fast retrieval.
"""

import hashlib
import json
import re
import sqlite3
import struct
from pathlib import Path
from typing import Iterator, Optional

from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

console = Console()

# --- Encoding detection ---

def detect_encoding(filepath: Path, sample_bytes: int = 4096) -> str:
    """Try UTF-8 first, fall back to GBK."""
    with open(filepath, "rb") as f:
        raw = f.read(sample_bytes)
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        raw.decode("gbk")
        return "gbk"
    except (UnicodeDecodeError, LookupError):
        pass
    try:
        raw.decode("gb18030")
        return "gb18030"
    except (UnicodeDecodeError, LookupError):
        pass
    return "utf-8"  # desperate fallback, will likely fail later


# --- Hard filters ---

AD_KEYWORDS = [
    "加微信", "付费", "全集下载", "请收藏", "求收藏", "求推荐",
    "www.", "http://", "https://", ".com", ".net", ".cn",
    "最新章节", "更新最快", "无弹窗", "无广告",
    "─" * 10, "★" * 5,
]

# Regex for garbled text: runs of characters not in common CJK/ASCII ranges
GARBLE_RE = re.compile(r"[^一-鿿　-〿＀-￯a-zA-Z0-9\s，。！？；：""''…—\n]{3,}")

# Regex for person-mixing: 她/他/我 switching more than 3 times in one passage
PRONOUN_SWITCH_RE = re.compile(r"她|他|我")


def hard_filter(passage: str) -> tuple[bool, str]:
    """Returns (reject, reason). True = reject."""
    text = passage.strip()

    if len(text) < 100:
        return True, "too_short"

    # Garbled text rate
    garbled = len(GARBLE_RE.findall(text))
    if garbled / max(len(text), 1) > 0.05:
        return True, "garbled"

    # Ad keywords
    text_lower = text.lower()
    for kw in AD_KEYWORDS:
        if kw.lower() in text_lower:
            return True, "ad_content"

    # Person pronoun chaos: she/he/I switching rapidly
    pronouns = PRONOUN_SWITCH_RE.findall(text)
    switches = sum(1 for i in range(1, len(pronouns)) if pronouns[i] != pronouns[i - 1])
    if switches > 15:
        return True, "pronoun_chaos"

    return False, ""


# --- SimHash dedup ---

def simhash(text: str) -> int:
    """63-bit simhash for Chinese text. Tokenizes by bigram characters.

    Masked to 63 bits so the value fits SQLite's signed 64-bit INTEGER
    (a 64-bit hash with the top bit set overflows the column type).
    """
    tokens = [text[i:i + 2] for i in range(len(text) - 1)]
    weights = [0] * 64
    for token in tokens:
        h = struct.unpack(">Q", hashlib.md5(token.encode()).digest()[:8])[0]
        for i in range(64):
            if h & (1 << i):
                weights[i] += 1
            else:
                weights[i] -= 1
    result = 0
    for i in range(64):
        if weights[i] > 0:
            result |= (1 << i)
    return result & 0x7FFFFFFFFFFFFFFF


def hamming(a: int, b: int) -> int:
    """Hamming distance between two 64-bit integers."""
    x = a ^ b
    count = 0
    while x:
        count += 1
        x &= x - 1
    return count


# --- Technique Density Scoring ---

# Sound words: onomatopoeia for sexual sounds
SOUND_WORDS = re.compile(r"啧啧|噗嗤|咕叽|汩汩|噗呲|啪嗒|咕嘟")

# Liquid words: terms for sexual fluids
LIQUID_WORDS = re.compile(r"淫水|浓精|爱液|蜜汁|白浊|精液|湿[了透成]|洇湿|淌|顺着.*[淌流滴]")

# Touch/sensation words
TOUCH_WORDS = re.compile(
    r"发烫|战栗|战[栗慄]|酥麻|酥软|酥[了痒]|麻[了痒]|颤抖|"
    r"腿软|收缩|绞紧|一紧|蠕动|痉挛|抽[搐动]|"
    r"脚趾蜷缩|弓起[背身腰]|绷[直紧]|瘫软|脱力"
)

# Organ-specific terms with action (not just naming)
ORGAN_ACTION = re.compile(
    r"(骚穴|嫩穴|小穴|蜜穴|花穴).{0,10}(收缩|绞紧|吮吸|喷|淌|湿|紧|热|"
    r"插|操|顶|抽|磨|碾|进出|裹|夹)|"
    r"(奶子|大奶|巨乳|乳房|双乳|奶).{0,10}(揉|捏|搓|晃|颤|"
    r"弹|变形|挤|压|泛红|白[得着]晃)"
)

# Full-body climax chain
CLIMAX_CHAIN = re.compile(
    r"(浑身|全身|整个人|身体).{0,5}(痉挛|抽[搐动]|弓起|绷[直紧])|"
    r"(眼前.{0,5}(发白|一[片黑]|模糊))|"
    r"(淫水|爱液|液体).{0,5}(喷[涌射出]|涌[出]|失禁)|"
    r"(穴肉|阴道|花径).{0,10}(剧烈|一阵).{0,5}(收缩|绞紧|痉挛)"
)

# Bystander reaction / environmental feedback (creates tension)
BYSTANDER_RE = re.compile(
    r"(怀疑|侧目|议论|窃窃私语|偷[看听瞄]|目光|视线|脚步声|逼近|"
    r"差一点|险些|几乎|差点|万一|被人|有人|旁人|"
    r"以为.{0,5}(听见|看见|发现|知道)|"
    r"屏[住息][呼吸]|捂住嘴|咬[住紧][嘴唇牙手背]|不敢[出声响]|强装)"
)

# Dialogue with character voice
DIALOGUE_SCORE = re.compile(
    r"(贱|骚|浪|欠操|想要|快[点些].{0,5}(操|插|干|要|给)|"
    r"老[爷子]|本王|本[座尊]|奴[家婢]|妾身|属下|殿下|"
    r"叫.{0,5}(出来|大声|给.{0,3}听))"
)


def score_passage(text: str) -> tuple[int, dict]:
    """Score a passage for technique density. Returns (total_score, breakdown)."""
    scores = {}
    scores["sound"] = len(SOUND_WORDS.findall(text))
    scores["liquid"] = len(LIQUID_WORDS.findall(text))
    scores["touch"] = len(TOUCH_WORDS.findall(text))
    scores["organ_action"] = len(ORGAN_ACTION.findall(text)) * 2
    scores["climax"] = len(CLIMAX_CHAIN.findall(text)) * 3
    scores["bystander"] = len(BYSTANDER_RE.findall(text))
    scores["dialogue"] = len(DIALOGUE_SCORE.findall(text))

    total = sum(scores.values())
    return total, scores


# --- Play type classification keywords ---

PLAY_PATTERNS = {
    "露出": re.compile(r"露出|走光|暴露|真空|没穿内|不穿内|衣下|帘后|背身|春光|弯腰.*领口"),
    "调教": re.compile(r"调教|驯[服化]|惩罚|跪|主人|奴隶|服从|听[话令命]|赏[赐罚]"),
    "偷情": re.compile(r"偷情|偷[欢腥吃]|出轨|背[着地里]|瞒着|幽会|私[通会]|人妻|有夫|老公.*不"),
    "多人": re.compile(r"群[交Pp]|多人|轮|一起|两人|三人|双[飞龙]|围观|众[人目]|满[屋堂殿]"),
    "纯爱": re.compile(r"温柔|爱[抚怜惜]|深情|缠绵|缱绻|柔情|慢慢|轻[轻柔缓]"),
    "制服": re.compile(r"制[服装]|军装|警服|护士|教师|OL|职场|公司|上[司级]|下[属级]|同事"),
    "古风": re.compile(r"王爷|皇上|陛下|臣妾|本[王宫]|殿下|侍女|丫鬟|青楼|王府|皇宫|朝代|夫君|娘子"),
    "现代": re.compile(r"公司|办公室|电梯|地铁|公交|手机|微信|酒店|酒吧|夜店|健身房|校园|大学|高中"),
    "仙侠": re.compile(r"修真|仙[人子魔]|修[炼行]|灵[气力根]|渡劫|飞升|练气|筑基|元婴|金丹|元神|法术|御[剑风]"),
    "乱伦": re.compile(r"妈妈|母子|父女|兄妹|姐弟|阿姨|叔[叔]|舅[舅]|表[兄妹姐弟]|岳母|儿媳|女婿"),
}


def classify_passage(text: str) -> list[str]:
    """Quick keyword-based classification. Returns list of likely play types."""
    results = []
    text_clean = text[:2000]  # first 2000 chars is enough for classification
    for play_type, pattern in PLAY_PATTERNS.items():
        if pattern.search(text_clean):
            results.append(play_type)
    return results or ["未分类"]


# --- File reader ---

def read_file(filepath: Path) -> Optional[str]:
    """Read a file with auto-detected encoding. Returns None on failure."""
    encoding = detect_encoding(filepath)
    try:
        with open(filepath, encoding=encoding, errors="replace") as f:
            return f.read()
    except Exception:
        return None


# --- Passage splitter ---

def split_passages(text: str, min_len: int = 100) -> list[str]:
    """Split text into passages by double newlines, merge short ones."""
    raw = re.split(r"\n\s*\n", text)
    passages = []
    buf = ""
    for p in raw:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) < min_len * 2:
            buf += "\n" + p if buf else p
        else:
            if len(buf) >= min_len:
                passages.append(buf)
            buf = p
    if len(buf) >= min_len:
        passages.append(buf)
    return passages


# --- Main indexer ---

def build_index(
    corpus_dir: str,
    db_path: str,
    anchor_files: Optional[list[str]] = None,
    min_score: int = 2,
):
    """Walk corpus_dir, index all .txt files into SQLite DB."""
    from pathlib import Path
    import os

    corpus = Path(corpus_dir)
    if not corpus.exists():
        console.print(f"[red]语料目录不存在: {corpus_dir}[/red]")
        return

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS passages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            passage_idx INTEGER NOT NULL,
            text TEXT NOT NULL,
            simhash INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            score_breakdown TEXT DEFAULT '{}',
            play_types TEXT DEFAULT '',
            char_count INTEGER DEFAULT 0,
            is_anchor INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON passages(score DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_play ON passages(play_types)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_simhash ON passages(simhash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_anchor ON passages(is_anchor)")

    # Collect anchor file names for marking
    anchor_names = set()
    if anchor_files:
        for f in anchor_files:
            anchor_names.add(Path(f).name)

    txt_files = list(corpus.rglob("*.txt"))
    console.print(f"找到 [bold]{len(txt_files)}[/bold] 个 txt 文件")

    stats = {"files": 0, "passages": 0, "kept": 0, "filtered": 0, "duplicates": 0}

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("索引语料库...", total=len(txt_files))

        for filepath in txt_files:
            stats["files"] += 1
            is_anchor = (filepath.name in anchor_names) or any(
                a in str(filepath) for a in anchor_names
            )

            text = read_file(filepath)
            if text is None:
                progress.advance(task)
                continue

            passages = split_passages(text)
            stats["passages"] += len(passages)

            for idx, passage in enumerate(passages):
                # Hard filter
                reject, reason = hard_filter(passage)
                if reject:
                    stats["filtered"] += 1
                    continue

                # Dedup via simhash
                sh = simhash(passage)
                # Check against existing in DB (simplified: check nearby hash band)
                existing = conn.execute(
                    "SELECT id FROM passages WHERE simhash = ? LIMIT 1", (sh,)
                ).fetchone()
                if existing:
                    # Wider check: any passage with hamming distance < 10
                    # For performance, only check same simhash for now
                    stats["duplicates"] += 1
                    continue

                # Score
                total, breakdown = score_passage(passage)
                if total < min_score and not is_anchor:
                    stats["filtered"] += 1
                    continue

                # Classify
                play_types = classify_passage(passage)

                # Insert
                conn.execute(
                    """INSERT INTO passages
                       (file_path, passage_idx, text, simhash, score, score_breakdown, play_types, char_count, is_anchor)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(filepath),
                        idx,
                        passage,
                        sh,
                        total,
                        json.dumps(breakdown, ensure_ascii=False),
                        ",".join(play_types),
                        len(passage),
                        1 if is_anchor else 0,
                    ),
                )
                stats["kept"] += 1

            conn.commit()
            progress.advance(task)

    conn.commit()

    # Report
    console.print(f"\n[green]索引完成:[/green]")
    console.print(f"  文件: {stats['files']}")
    console.print(f"  段落(原始): {stats['passages']}")
    console.print(f"  保留: {stats['kept']}")
    console.print(f"  过滤(低质): {stats['filtered']}")
    console.print(f"  去重: {stats['duplicates']}")

    # Per-play-type stats
    for pt in PLAY_PATTERNS:
        count = conn.execute(
            "SELECT COUNT(*) FROM passages WHERE play_types LIKE ?", (f"%{pt}%",)
        ).fetchone()[0]
        if count > 0:
            console.print(f"  [{pt}]: {count} 段")

    conn.close()
    return stats


def search_passages(
    db_path: str,
    play_types: Optional[list[str]] = None,
    keywords: Optional[str] = None,
    min_score: int = 5,
    limit: int = 20,
    anchor_only: bool = False,
) -> list[dict]:
    """Search indexed passages by play type, keywords, and score threshold."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM passages WHERE score >= ?"
    params = [min_score]

    if anchor_only:
        query += " AND is_anchor = 1"

    if play_types:
        clauses = " OR ".join(["play_types LIKE ?" for _ in play_types])
        query += f" AND ({clauses})"
        params.extend(f"%{p}%" for p in play_types)

    query += " ORDER BY score DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        if keywords:
            kw_set = set(keywords.split())
            text = d["text"]
            # Simple relevance: count keyword occurrences
            relevance = sum(text.count(kw) for kw in kw_set)
            if relevance == 0:
                continue
            d["relevance"] = relevance
        results.append(d)

    conn.close()

    # Sort by relevance if keywords provided
    if keywords:
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

    return results[:limit]


def search_anchor_baseline(db_path: str) -> dict:
    """Compute technique density baseline from anchor works."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT score_breakdown, score FROM passages WHERE is_anchor = 1"
    ).fetchall()
    conn.close()

    if not rows:
        return {}

    import json
    all_breakdowns = []
    scores = []
    for row in rows:
        try:
            all_breakdowns.append(json.loads(row[0]))
        except (json.JSONDecodeError, TypeError):
            pass
        scores.append(row[1])

    # Average per dimension
    dims = ["sound", "liquid", "touch", "organ_action", "climax", "bystander", "dialogue"]
    avg = {}
    for dim in dims:
        vals = [b.get(dim, 0) for b in all_breakdowns]
        avg[dim] = sum(vals) / len(vals) if vals else 0

    scores.sort()
    n = len(scores)
    return {
        "avg_total": sum(scores) / n if n else 0,
        "median_total": scores[n // 2] if n else 0,
        "p25_total": scores[n // 4] if n > 4 else 0,
        "p75_total": scores[3 * n // 4] if n > 4 else 0,
        "avg_breakdown": avg,
        "sample_count": n,
    }
