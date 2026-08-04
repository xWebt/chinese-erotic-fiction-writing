"""Chapter generator: DeepSeek API-powered chapter writing with auto-continue.

Core innovation: breaks each chapter into 3-4 scene segments, generates each
segment independently, then auto-continues any segment that falls short of
its word count target. Handles context threading between segments.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import yaml
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .prompt_templates import (
    CHAPTER_OUTLINE,
    GENERATE_SCENE,
    CONTINUE_SCENE,
    STYLE_REFERENCE,
)
from .corpus_indexer import search_passages

console = Console()


def _count_chinese(text: str) -> int:
    """Count Chinese characters (excluding punctuation and whitespace)."""
    return len(re.findall(r"[一-鿿]", text))


def _count_total(text: str) -> int:
    """Count total characters (including punctuation) after stripping markdown."""
    cleaned = re.sub(r"[#\-\*>\s]", "", text)
    return len(cleaned)


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    input_cost = prompt_tokens / 1_000_000 * 0.14
    output_cost = completion_tokens / 1_000_000 * 0.28
    return round(input_cost + output_cost, 4)


class ChapterGenerator:
    """Generates a full chapter using DeepSeek API with segmented generation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        db_path: Optional[str] = None,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.db_path = db_path
        self.total_cost = 0.0

    def generate_outline(
        self,
        play_types: list[str],
        setting: str,
        perspective: str,
        target_words: int,
        playbooks_dir: Optional[str] = None,
        previous_context: str = "",
    ) -> str:
        """Generate a detailed scene-segmented chapter outline."""
        # Load relevant playbook rules
        playbook_rules = ""
        if playbooks_dir:
            playbook_rules = self._load_playbook_rules(playbooks_dir, play_types)

        prompt = CHAPTER_OUTLINE.format(
            play_types=", ".join(play_types),
            setting=setting,
            perspective=perspective,
            target_words=target_words,
            playbooks=playbook_rules or "（使用默认技法规则）",
            previous_context=previous_context or "（新章开始，无前情）",
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.7,
        )
        self._track_cost(response)

        return response.choices[0].message.content or ""

    def generate_scene(
        self,
        scene_brief: str,
        playbook_rules: str,
        characters: str,
        previous_scene: str,
        target_words: int,
        style_references: Optional[str] = None,
    ) -> str:
        """Generate a single scene. Returns the scene text."""
        prompt = GENERATE_SCENE.format(
            scene_brief=scene_brief,
            playbook_rules=playbook_rules,
            characters=characters,
            previous_scene=previous_scene,
            target_words=target_words,
        )

        if style_references:
            ref_prompt = STYLE_REFERENCE.format(reference_passages=style_references)
            prompt = prompt + "\n\n" + ref_prompt

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.8,
        )
        self._track_cost(response)

        return response.choices[0].message.content or ""

    def continue_scene(
        self,
        current_text: str,
        current_words: int,
        target_words: int,
        ending_chars: int = 300,
    ) -> Optional[str]:
        """Continue writing a scene that fell short. Returns continuation or None."""
        remaining = target_words - current_words
        if remaining <= 100:
            return None

        ending = current_text[-ending_chars:] if len(current_text) > ending_chars else current_text

        prompt = CONTINUE_SCENE.format(
            current_words=current_words,
            remaining_words=remaining,
            ending_text=ending,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.8,
        )
        self._track_cost(response)

        return response.choices[0].message.content or None

    def generate_chapter(
        self,
        play_types: list[str],
        setting: str,
        perspective: str = "第三人称",
        target_words: int = 5000,
        characters: str = "",
        previous_context: str = "",
        playbooks_dir: Optional[str] = None,
        max_continue_rounds: int = 4,
        inject_references: bool = True,
    ) -> dict:
        """Generate a full chapter end-to-end.

        Returns:
            dict with keys: title, outline, scenes, full_text, word_count, cost
        """
        console.print(f"[bold]生成章节[/bold]: {setting} | 玩法: {', '.join(play_types)}")

        # Step 1: Generate outline
        console.print("  [dim]生成大纲...[/dim]")
        outline = self.generate_outline(
            play_types, setting, perspective, target_words,
            playbooks_dir, previous_context,
        )
        if not outline:
            return {"error": "大纲生成失败"}
        console.print(Panel(outline[:500], title="大纲"))

        # Step 2: Parse scenes from outline
        scenes = self._parse_scenes(outline, target_words)
        if not scenes:
            console.print("[yellow]未能从大纲中解析场景分段，使用单场景模式[/yellow]")
            scenes = [{"brief": outline[:200], "words": target_words}]

        console.print(f"  解析出 [bold]{len(scenes)}[/bold] 个场景段")

        # Step 3: Load playbook rules
        playbook_rules = (
            self._load_playbook_rules(playbooks_dir, play_types)
            if playbooks_dir else ""
        )

        # Step 4: Get style references from indexed corpus
        style_refs = None
        if inject_references and self.db_path:
            style_refs = self._get_style_references(play_types, setting)

        # Step 5: Generate each scene
        scene_texts = []
        prev_scene = previous_context[-500:] if previous_context else ""

        for i, scene in enumerate(scenes):
            words_per = scene.get("words", target_words // len(scenes))
            brief = scene.get("brief", f"场景 {i + 1}")

            console.print(f"  [cyan]场景 {i + 1}/{len(scenes)}[/cyan]: {brief[:60]}... (目标 {words_per}字)")

            text = self.generate_scene(
                brief, playbook_rules, characters, prev_scene,
                words_per, style_refs,
            )

            if not text:
                console.print(f"  [red]场景 {i + 1} 生成失败[/red]")
                continue

            # Step 5b: Auto-continue if too short
            word_count = _count_total(text)
            continue_round = 0
            while word_count < words_per * 0.7 and continue_round < max_continue_rounds:
                continue_round += 1
                console.print(f"    [dim]字数 {word_count}/{words_per}，续写第 {continue_round} 轮...[/dim]")
                continuation = self.continue_scene(text, word_count, words_per)
                if continuation:
                    text += "\n\n" + continuation
                    word_count = _count_total(text)
                else:
                    break

            if continue_round > 0:
                console.print(f"    [green]续写完成: {word_count} 字 (共 {continue_round} 轮)[/green]")

            scene_texts.append(text)
            prev_scene = text[-300:]  # Last 300 chars as context for next scene

        # Step 6: Assemble full chapter
        full_text = "\n\n".join(scene_texts)
        total_words = _count_total(full_text)
        hanzi = _count_chinese(full_text)

        console.print(f"  [bold green]章节完成: {total_words} 总字符 / {hanzi} 汉字 | 成本: ${self.total_cost:.4f}[/bold green]")

        return {
            "outline": outline,
            "scenes": scene_texts,
            "full_text": full_text,
            "total_chars": total_words,
            "hanzi": hanzi,
            "cost": round(self.total_cost, 4),
        }

    def _parse_scenes(self, outline: str, total_words: int) -> list[dict]:
        """Parse scene segments from the LLM-generated outline."""
        scenes = []

        # Try to find numbered scene descriptions
        # Pattern: "场景1：..." or "1. ..." or "第一段：..."
        patterns = [
            r"(?:场景|第)[一二三四五六七八九十\d]+[段部分]?[：:](.*?)(?=(?:场景|第)[一二三四五六七八九十\d]+[段部分]?[：:]|\Z)",
            r"\d+[\.\、\)]\s*(?:场景|段)[：:]?\s*(.+?)(?=\d+[\.\、\)]\s*(?:场景|段)|\Z)",
            r"\d+[\.\、\)]\s*(.+?)(?=\d+[\.\、\)]\s|\Z)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, outline, re.DOTALL)
            if len(matches) >= 2:
                for m in matches:
                    m = m.strip()
                    if len(m) > 10:
                        scenes.append({"brief": m[:200]})
                break

        if not scenes:
            # Fallback: treat entire outline as one scene
            scenes = [{"brief": outline[:300]}]

        # Distribute word count
        if scenes:
            base = total_words // len(scenes)
            # Give slightly more words to middle scenes (H main body)
            for i, s in enumerate(scenes):
                if i == 0 or i == len(scenes) - 1:
                    s["words"] = int(base * 0.8)  # intro/outro shorter
                else:
                    s["words"] = int(base * 1.2)  # main body longer

        return scenes

    def _load_playbook_rules(self, playbooks_dir: str, play_types: list[str]) -> str:
        """Load relevant playbook iron rules as compact text."""
        if not playbooks_dir or not Path(playbooks_dir).exists():
            return ""

        rules = []
        for f in Path(playbooks_dir).glob("*.yaml"):
            try:
                with open(f) as fp:
                    data = yaml.safe_load(fp)
                name = data.get("name", f.stem)
                # Check if this playbook matches any requested play type
                if any(pt in name or name in pt for pt in play_types):
                    iron = data.get("iron_rules", [])
                    if isinstance(iron, list):
                        rules.append(f"【{name}】\n" + "\n".join(f"- {r}" for r in iron))
                    elif isinstance(iron, str):
                        rules.append(f"【{name}】\n{iron}")
            except Exception:
                pass

        return "\n\n".join(rules)

    def _get_style_references(
        self, play_types: list[str], setting: str, limit: int = 3
    ) -> Optional[str]:
        """Search indexed corpus for style reference passages."""
        if not self.db_path:
            return None

        keywords = " ".join(play_types) + " " + setting
        results = search_passages(
            self.db_path,
            play_types=play_types,
            keywords=keywords,
            min_score=5,
            limit=limit,
        )

        if not results:
            return None

        refs = []
        for r in results:
            # Take a middle excerpt (not the start, often setup text)
            text = r["text"]
            mid = len(text) // 3
            excerpt = text[mid:mid + 400]
            refs.append(excerpt)

        return "\n\n---\n\n".join(refs)

    def _track_cost(self, response):
        """Track API cost from response usage."""
        if hasattr(response, "usage") and response.usage:
            cost = _estimate_cost(
                self.model,
                response.usage.prompt_tokens or 0,
                response.usage.completion_tokens or 0,
            )
            self.total_cost += cost


# --- Convenience function ---

def generate_chapter(
    api_key: str,
    play_types: list[str],
    setting: str,
    perspective: str = "第三人称",
    target_words: int = 5000,
    characters: str = "",
    previous_context: str = "",
    playbooks_dir: Optional[str] = None,
    db_path: Optional[str] = None,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    max_continue_rounds: int = 4,
) -> dict:
    """Convenience function to generate one chapter."""
    gen = ChapterGenerator(
        api_key=api_key,
        base_url=base_url,
        model=model,
        db_path=db_path,
    )
    return gen.generate_chapter(
        play_types=play_types,
        setting=setting,
        perspective=perspective,
        target_words=target_words,
        characters=characters,
        previous_context=previous_context,
        playbooks_dir=playbooks_dir,
        max_continue_rounds=max_continue_rounds,
    )
