#!/usr/bin/env python3
"""统计 H 向小说正文字数，按章节输出，用于验证字数目标。

用法:
    python3 wordcount.py <正文.txt> [达标字符数]

输出:
    每章: 总字符(含标点) + 汉字数；结尾: 全书总计 + 达标章数
    达标线默认 5000 字符（可用第二参数调整）

支持标题格式:
    ### 第N章 XXX       (旧 md 格式，兼容)
    第N章 XXX            (txt 格式)
    ### 番外X：XXX       (旧 md 番外)
    番外X：XXX           (txt 番外)
"""
import re
import sys


def main():
    if len(sys.argv) < 2:
        print("用法: python3 wordcount.py <正文.txt> [达标字符数]")
        sys.exit(1)
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    text = open(sys.argv[1], encoding="utf-8").read()

    # Chapter headers: 第N章 or 番外[数字]：标题.
    # Split and name regexes must stay consistent, or titles/body misalign.
    # 番外 REQUIRES digits and/or a delimiter (：or :) — bare "番外" is not a header.
    # 第N章 stays Arabic-numeral here; Chinese-numeral chapters are handled by
    # the line-anchored fallback below (avoids matching 第十三章 mid-sentence).
    title_re = r"(?:###\s*)?(?:第\d+章|番外[一二三四五六七八九十\d]*[：:])"
    chapters = re.split(title_re, text)
    names = re.findall(r"(?:###\s*)?((?:第\d+章|番外[一二三四五六七八九十\d]*[：:])[^\n]*)", text)

    if not names:
        # Try single-chapter file (just a title at the start)
        chapters = re.split(r"(?:^|\n)(?:第[一二三四五六七八九十\d]+章)", text)
        names = re.findall(r"(?:第[一二三四五六七八九十\d]+章[^\n]*)", text)

    if not names:
        print("未找到章节标题（支持格式：第N章 XXX 或 ### 第N章 XXX 或 番外X：XXX）")
        sys.exit(1)

    total = 0
    ok = 0
    for name, ch in zip(names, chapters[1:]):
        body = re.sub(r"[#\-\*>\s]", "", ch)
        hanzi = len(re.findall(r"[一-鿿]", body))
        total += hanzi
        flag = "OK" if len(body) >= threshold else (
            "--" if len(body) >= threshold * 0.5 else "SHORT")
        if len(body) >= threshold:
            ok += 1
        print(f"{flag} {name.strip()}: 总字符{len(body)} 汉字{hanzi}")
    print(f"总计: {total} 汉字 | 达标 {ok}/{len(names)} 章 (阈值 {threshold} 字符)")


if __name__ == "__main__":
    main()
