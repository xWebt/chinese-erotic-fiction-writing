#!/usr/bin/env python3
"""统计 H 向小说正文字数，按章节输出，用于验证 5-6k 字/章目标。

用法:
    python3 wordcount.py <正文.md> [达标字符数]

输出:
    每章: 总字符(含标点) + 汉字数；结尾: 全书总计 + 达标章数
    达标线默认 5000 字符（可用第二参数调整，如 3500 用于番外宽松线）
    汉字数 = 中文字符数（不含标点/英文/数字）

支持标题格式:
    ### 第N章 XXX      （正传）
    ### 番外X：XXX     （番外，v4 大纲要求番外也要计字数）
"""
import re
import sys


def main():
    if len(sys.argv) < 2:
        print("用法: python3 wordcount.py <正文.md> [达标字符数]")
        sys.exit(1)
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    text = open(sys.argv[1], encoding="utf-8").read()

    chapters = re.split(r"### (?:第\d+章|番外)", text)
    names = re.findall(r"### ((?:第\d+章|番外)[^\n]*)", text)
    if not names:
        print("未找到章节标题（### 第N章 或 ### 番外X）")
        sys.exit(1)

    total = 0
    ok = 0
    for name, ch in zip(names, chapters[1:]):
        body = re.sub(r"[#\-\*>\s]", "", ch)
        hanzi = len(re.findall(r"[\u4e00-\u9fff]", body))
        total += hanzi
        flag = "OK" if len(body) >= threshold else (
            "--" if len(body) >= threshold * 0.5 else "SHORT")
        if len(body) >= threshold:
            ok += 1
        print(f"{flag} {name}: 总字符{len(body)} 汉字{hanzi}")
    print(f"总计: {total} 汉字 | 达标 {ok}/{len(names)} 章 (阈值 {threshold} 字符)")


if __name__ == "__main__":
    main()
