# Google Android Agent Development Stack

这是 AEGL 系统中的契约、编排和验收源码仓，不是图片分析业务项目。
AEGL 负责权限与受控执行；本仓负责把需求编译成冻结契约，通过 Bridge 连接
固定 ChatGPT 会话与 Hermes，并组织确定性验证和结果回传。

**从这里开始：[系统中文使用教程](docs/SYSTEM-USAGE.zh-CN.md)。**
本轮核对记录见 [2026-11-11 定点验证](docs/VALIDATION-2026-11-11.md)。

| 目录 | 职责 |
|---|---|
| `specification/` | 离线生成和验证契约，产生 READY；不调用模型 |
| `orchestration/hermes/bridge/` | 单轮协议、链状态、受信项目绑定和受控执行入口 |
| `orchestration/hermes/supervisor/` | 有轮数和时间上限的前台 campaign |
| `verification/` | 确定性验证、设备锁、结果和失败证据 |
| `evaluation/` | 评估和观察，不代替授权与业务验收 |
| `scripts/` | 路径契约、主机准备预演、布局检查 |

系统另一仓为 [AI-Engineering-Governance-Layer](https://github.com/zgz314159/AI-Engineering-Governance-Layer)。
Hermes 与 Browser-Harness 是外部依赖；锁定信息在
[`HERMES-LOCK.json`](orchestration/hermes/HERMES-LOCK.json)，不复制其源码到本仓。

源码分支、正式树、`/usr/local/lib` 中已安装组件和 XDG 运行状态是不同对象。
提交或 push 不等于安装；克隆成功也不等于跨机器受控环境已经部署完成。
当前机器的最短路径、浏览器恢复、任务流程和新机器尚缺的条件均在教程中。
