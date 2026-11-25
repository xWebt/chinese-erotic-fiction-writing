# 中文成人小说写作 Skill v1.1

面向 AI 代理的中文成人向小说工具箱。默认现代白话、第三人称贴身、对白和动作推进、低比喻。

## 使用

```bash
pip install -e .
novel styleprofile <书库目录或文件...>
novel scenes <长篇.txt> --count 6
novel stylecheck <正文.txt> --profile plain-modern
novel tokenaudit <Codex session.jsonl>
```

## 结构

```text
SKILL.md             唯一入口
core/                场景、文风、亲密场景、改稿和上下文规则
styles/              从锚点作品提取的文风指纹
playbooks/           15 个单场景玩法卡
harness/             统计、场景抽取、文风检查和 token 检查
tests/               单元与契约测试
```

默认只加载 `SKILL.md`、`core/prose-rules.md`、`styles/plain-modern.yaml` 和一张玩法卡。

## 主声线

`plain-modern` 来自《重生之官路商途》的非性叙事和对白：

- 现代白话；
- 具体职业与空间细节；
- 对白承担信息；
- 比喻约 0.7 个/千字；
- 连续纯叙述短段最多 2 个；
- 禁止告示牌式说明；
- 禁止连续动作标签。

## 专项模块

- `first-person-comic`：第一人称和幽默；
- `adult-adventure`：成人场景与剧情融合；
- `classical-wuxia`：动作调度和多人群像；
- `readable-fantasy`：长篇可读性和信息推进。

专项模块只读强项，不改变主声线。

## 安全

默认角色为成年人、自愿。

## 测试

```bash
python -m unittest discover -s tests -v
```

缺少 PyYAML 的 runtime 会跳过 profile YAML 测试；安装项目依赖后可完整执行。
