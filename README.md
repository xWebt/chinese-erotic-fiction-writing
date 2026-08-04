# 中文成人向（H）小说创作 · 白纸工具包

A white-paper toolkit for writing Chinese adult (H) fiction with AI agents.

**不预设任何玩法、笔触、题材或字数。每个用户打开都是一张白纸，一切偏好由勘察确定。**

本仓库是一套**方法论 + 本地工具**：交给 AI 代理（Claude Code）用来写、扩写、重写中文 H 小说，同时内置本地语料库学习与用户会话记忆。所有参考文件均为**脱敏后的通用模板**，公开内容不含任何真实角色名、本地路径或用户身份。

## 核心原则

| 原则 | 含义 |
|---|---|
| **白纸原则（P0）** | 不绑定任何玩法/笔触/字数目标。动笔前必须勘察，只有用户明确提供的偏好才存在。 |
| **隐私（P0）** | `sessions/` 用户胶囊绝不离开本机。所有公开内容均脱敏。 |
| **身体反应优先** | 用身体反应代替叙述：发烫 / 战栗 / 湿透 / 腿软 / 收缩 / 喷水。 |
| **高潮写足** | 痉挛 → 弓起 → 脚尖绷直 → 收缩 → 喷涌 → 眼前发白 → 脱力，不能一句带过。 |
| **声音 + 液体成对** | 啧啧/咕叽 与 汩汩/顺着淌 必须同时出现，无"干动作"。 |
| **多维描写** | 每个器官至少覆盖 3-4 个维度（形状 / 触感 / 声音 / 视觉 / 状态）。 |

## 三层架构

| 层级 | 位置 | 内容 | 公开？ |
|---|---|---|---|
| L1 通用 | `SKILL.md` + `references/` | 纯方法论 | ✅ |
| L2 沉淀 | `references/` | 跨用户脱敏技法模板 | ✅ |
| L3 会话 | `sessions/` | 每用户胶囊（偏好 + 反馈日志 + 风格指纹） | **否** |

## 它能做什么

- **写小说**：完整的 H 场景写法、章节结构、高潮编排、多章规划方法论（见 `SKILL.md` / `CLAUDE.md`）。
- **学习本地书库**：索引你自己的 `.txt` 书库，提取玩法模式与技法密度，转成脱敏的风格约束。
- **会话记忆**：每次交互追加反馈日志，风格指纹逐步收敛到该用户口味，越用越准。
- **本地 CLI 工具**：纯本地操作，零 API 依赖。

## 安装

```bash
pip install -e .
```

要求 Python ≥ 3.10。

## CLI 用法

`novel` 命令组提供本地工具（不联网、无 API 调用）：

```bash
# 索引本地 .txt 小说库（自动识别 UTF-8/GBK，质量过滤 + 去重 + 技法评分 + 玩法分类 → SQLite）
novel index -d <书库目录>

# 用已知佳作锚点计算技法密度基线，用于后续评分阈值
novel calibrate -a <锚点匹配模式> [--strictness 0.5]

# 分章字数统计，带达标/未达标判定
novel wordcount <章节.txt> [--threshold 5000]

# 语料库索引统计
novel stats
```

不安装直接运行：

```bash
PYTHONPATH="$仓库目录" python -m harness.cli --help
```

## 在 Claude Code 中使用

技能本体定义在 `SKILL.md`（Claude Code skill 格式）：

1. 将本仓库（或 `SKILL.md` + `references/`）放入你的 skills 目录 / 让 Claude Code 指向本仓库。
2. 提出写 / 扩写 / 重写中文 H 小说的请求。
3. 技能会**先勘察**（性别/笔触、玩法取向、题材形式、单章字数、禁忌清单），把结果写入 `sessions/` 胶囊，再动笔。

勘察时可指定**本地书库目录**——技能会先学习你书库里的风格再动笔。书库仅用于本地学习，绝不上传或写入任何公开内容。

## 仓库结构

```
SKILL.md              技能定义 + 会话学习规范
CLAUDE.md             完整代理指令
AGENTS.md             仓库级代理快速上手
references/           脱敏技法/玩法模板
  carnal-writing-techniques.md       高浓度肉欲写法技巧
  quiet-exposure-techniques.md       悄悄露出（隐秘暴露）模板
  tech-toy-play-techniques.md        情趣玩具 / 远程控制
  domination-training-techniques.md  调教 / 主奴（权力交换）
  group-play-techniques.md           多人 / 群交空间调度
harness/              本地 Python 工具（cli / index / calibrate / prompts）
scripts/              辅助脚本（wordcount / batch_insert）
sessions/             用户胶囊 —— gitignore，仅本地
```

## 隐私保障

- `sessions/` 在 `.gitignore` 中，永不提交、永不推送。
- 所有参考文件均已脱敏——公开仓库不含任何真实名字、路径或用户身份。
- 你的书库、大纲、章节正文全部留在你自己的输出目录。
