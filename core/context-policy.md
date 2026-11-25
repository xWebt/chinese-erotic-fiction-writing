# 上下文加载策略

## 默认写作包

- `SKILL.md`
- `core/prose-rules.md`
- `styles/plain-modern.yaml`
- 一个 `playbooks/*.yaml`

默认不读取：

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- 全部 `styles/`
- 全部 `playbooks/`
- 旧 `references/`

## 可选模块

最多再加载一个：

- `styles/first-person-comic.yaml`
- `styles/adult-adventure.yaml`
- `styles/classical-wuxia.yaml`
- `styles/readable-fantasy.yaml`

## 参考书库

1. `novel styleprofile` 先看汇总；
2. `novel scenes` 最多抽 6 个短场景；
3. 每本最多精读 3 个场景；
4. 不把整章、整本或大规模搜索结果放进上下文。

## 编辑任务

- 同一文件不重复读取；
- 仓库修改先提纲，再批量提交；
- 避免逐行微补丁；
- 工具输出只保留命中和摘要。

## Token 预算

- 默认写作参考控制在 `6,000 至 8,000 tokens`；
- 项目开发与小说创作分开线程；
- 生成后只做一次风格检查和一次针对性修订。
