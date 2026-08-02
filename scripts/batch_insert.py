#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""锚点批量插入脚本（幂等）——把已落位的短骨架章节扩写到目标字数。

用法：
1. 复制本文件为工作区的 expand.py，把 PATH 改成目标正文文件
2. 往 INS 里填 (锚点, 插入文本) 对：
   - 锚点 = 原文"段落结尾的整句"，20-60 字，全文必须唯一（优先取对白回合结尾、
     身体反应句、场景转折句；绝不取自己之前插入过的文本，否则二次插入切碎段落）
   - 插入文本 = 150-400 字新段落（自玩细节、旁观议论、身体反应、对白回合、余韵钩子）
3. 运行 python3 expand.py，每轮后跑 wordcount.py 核对每章字数缺口再补

幂等三重检查（可反复运行）：
- 锚点缺失 -> SKIP 报告（多半是错记原文，用 content.find 验证锚点）
- 锚点重复 -> SKIP（多半是锚点取自插入文本，换锚点）
- 插入文本已存在 -> SKIP（已插入过）

注意：INS 内容含大量引号对白，新增条目用 write_file 写独立 fixN.py
（r'''...''' 原始三引号包裹），在结构标记 "\n]\n\ndef main():" 处插入，
不要用 patch 改本文件（patch 模糊匹配会截断含引号的文本行）。
"""
import sys

PATH = "正文.md"  # 目标正文文件路径

INS = [
    # ("唯一锚点整句", "插入的新段落"),
]

def main():
    with open(PATH, encoding="utf-8") as f:
        content = f.read()
    ok = skip_missing = ambiguous = already = 0
    items = []
    for anchor, text in INS:
        items.append((content.find(anchor), anchor, text))
    items.sort(key=lambda x: x[0], reverse=True)  # 降序插入，防位置偏移
    for idx, anchor, text in items:
        if idx == -1:
            print(f"SKIP 锚点缺失: {anchor[:24]}...")
            skip_missing += 1
            continue
        if content.count(anchor) > 1:
            print(f"SKIP 锚点重复x{content.count(anchor)}: {anchor[:24]}...")
            ambiguous += 1
            continue
        if text in content:
            print(f"SKIP 已插入: {anchor[:24]}...")
            already += 1
            continue
        content = content.replace(anchor, anchor + "\n\n" + text)
        ok += 1
        print(f"OK    {anchor[:24]}...")
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n完成: 插入{ok} 跳过(缺失{skip_missing}/重复{ambiguous}/已插{already})")

if __name__ == "__main__":
    main()
