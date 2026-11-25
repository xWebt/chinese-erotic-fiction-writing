# Playbook Index

默认只加载与当前场景最接近的一张卡。

| ID | 用途 | 推荐模块 |
|---|---|---|
| `quiet-exposure` | 差一点被发现 | `adult-adventure` |
| `remote-toy` | 远程操控与外表镇定 | `adult-adventure` |
| `public-solo` | 单人半公共空间 | `adult-adventure` |
| `mirror` | 倒影与自我观看 | 无 |
| `car` | 狭小空间和外界风险 | `adult-adventure` |
| `office-after-hours` | 下班后的职场空间 | `adult-adventure` |
| `affair` | 隐瞒关系的风险 | `first-person-comic` |
| `voice-call` | 声音和远程交流 | `first-person-comic` |
| `power-exchange` | 规则、许可和权力变化 | `adult-adventure` |
| `roleplay` | 称谓和角色身份 | `first-person-comic` |
| `group` | 多人空间调度 | `adult-adventure` |
| `long-term-couple` | 熟悉关系和旧问题 | `first-person-comic` |
| `stranger-brief` | 陌生人短暂互动 | 无 |
| `hotel-night` | 酒店、旅途、第二天 | `adult-adventure` |
| `bathhouse` | 浴室、温泉和水声 | `adult-adventure` |

`avoid` 和 `profile_modules` 是硬字段。玩法卡只提供结构，不提供可直接复制的句子。

读取顺序：`index.yaml` → 一张玩法卡。不要一次加载全部玩法。
