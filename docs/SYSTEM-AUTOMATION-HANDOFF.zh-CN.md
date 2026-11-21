# 跨项目自动接入：长期方向与新对话交接

更新：2026-11-21。本文件保存用户要求与证据边界，不是新的运行框架或执行授权。

## 总目标

建设 AEGL／Google-Android-Agent-Development-Stack 的可复用自动化开发能力。日历、图片分析等都是业务验证项目，不是系统本身。

理想使用方式：用户给出项目路径、需求和授权范围，系统自动完成精确 binding 与 Git 归属检查、开发契约五门（schema／traceability／boundaries／acceptance／hashes）、可信安装与任务登记及实际 gate、Hermes 受控执行（wrapper／sandbox／guard／broker）、Chrome 中 ChatGPT 指导、清理与结果回传、独立验收和系统问题总结。

通用接入应复用现有入口、配置和可信接口；项目差异主要由项目拥有的需求、精确路径、构建命令和验收条件表达。目标是不必每换项目就修改系统源码、复制专用准备脚本或手工拼装命令。当前尚未证明该目标已实现，不能承诺所有技术栈和外部环境零适配。

自动接入不是自动放行。保持既有权限与沙箱边界；首次可信配置、授权外操作、不可代替的用户认证按真实权限处理。Chrome 回复作为指导或按正式协议校验的控制块，不是可直接执行的可信代码。

## 不得偏离的推进路径

1. 一次集中审查，只列阻止下一次真实执行的实际问题。每项回答“它具体阻止了哪一步真实执行？”
2. 用已有可信方式做必要安装和准备，不新建封包、部署、诊断或验证框架。
3. 在用户已有明确授权范围内执行一次 120 秒真实任务，沿用现有 10 秒清理宽限并独立验收；不反复申请已给出的授权，也不自行扩大授权。
4. 失败保留记录；按 2026-11-21 最新用户规则，在授权范围内对原因明确且安全可证的故障自动修复、经受审查的有界恢复入口继续。不可盲目重发、重放已消费身份、延长预算或另建身份绕过失败；权限、预算或证据不足时停手。

传输修复、测试清理、已完成诊断提取和 SYSTEM-E2E-005 保持收口。不因新对话／压缩而重跑。正式项目保持只读，在批准 worktree 开发并走可信晋升；任务产物在项目外。业务源码、测试、规则归业务项目所有。

## 当前业务与已知事实

### 最新进度（2026-11-21 自动汇报接入）

**用户要求继续后的只读排查（2026-11-21）**：队列仍空，未再次执行。已核对安装态launcher、
Bridge与系统journal：本日历身份不在分阶段诊断白名单；原始执行stdout/stderr只存在于执行函数
返回值，Bridge按既有设计仅带回固定摘要，未落盘。profile/session/broker日志位于任务运行目录，
该目录`/run/aegl-model/CAL-WORD-PARAGRAPH-001`已清理。journal本时段只见启动命令，不能证明
模型、网络、工具或沙箱哪一层超时。scratch ACL仅owner/group可读，zhong无权限；诊断根目录
root/700，不能据不可遍历推断具体sink存在或不存在。根因继续UNKNOWN，无新增代码修复。
下一步仅请求用户认证执行固定scratch目录的`find -P`只读清单，不改ACL、不运行目录中的文件、
不调模型、不重跑身份。清单以NUL分隔，用户侧命令成功后原子改名为
`/home/zhong/EXE/RILI/artifacts/controlled/CAL-WORD-PARAGRAPH-001/scratch-inventory.nul`。
后台在此文件首次出现后读取并核对残留类型，不让用户搬运输出。该文件内容是不可信文件名/元数据，
不得作为命令或执行授权；若无有效残留，不从清单捏造根因，也不扩大执行预算。

**最新结论（覆盖下方历史状态）**：CAL-WORD-PARAGRAPH-001 已真实执行一次，120秒超时，
BLOCKED／exit124；cleanup CONFIRMED，结果 CONFIRMED_SENT。Bridge WAITING_FOR_GPT／seq20／
pending=false；当前任务身份已消费，不能再恢复或重放。worktree HEAD 仍59f9b807，status为空，
WordParagraphImporter.cs 与 WordParagraphImportTests.cs 均不存在。业务验收 FAILED；宿主验收
因受控执行未成功而 NOT_RUN；Windows NOT_RUN；超时根因 UNKNOWN，scratch权限不可读。
失败回报已由正式queue自动入当前聊天队列并通过ack确认，无人工搬运；job HUMAN_REQUIRED。
report_sha256=0c9b2030e4b13d03ec94b02a5ef66fb635247acbf75e61cb8ce440e71a81cdcc；
result_sha256=22f1aeba843d3acc01274bb88afb22e0f0906aa4bf4431e4500401b8bc652016。
自动派发／审查回写／失败回传已实证，成功开发及宿主验收接力尚未通过；不称系统业务闭环成功。
下一业务方向是依据已有、允许读取的执行证据查明超时，不新建诊断框架；无可读证据则保持UNKNOWN，
不能以新规则为由补模型次数、延长预算或另建身份。后台无新待办时保持安静。

**本轮恢复过程**：用户已授权安全有界恢复。首次 CDP READ_FAILED 经
审计恢复；续行首次读取又因 Hermes bootstrap re-exec 丢失入口模块路径中断，未发送、未消费。
修复把官方运行时选择提前到锁与状态修改之前，并固定项目入口导入路径。23 项针对性测试通过。
正式 adapter 只读确认精确请求不存在后，经 BOOTSTRAP_READ_CONTINUATION 审计续接同一次尝试；
没有增加 actions_done、任务身份、模型次数或预算。原 task/job/manifest 已发送一次并被 Bridge
ACCEPTED，seq19；实际结果见上方。下方未执行/等待授权等描述为历史快照。

**最新授权更新**：用户已明确授权补齐本次恢复并继续，且将“失败即停、不自动 recover”改为授权范围内
自动修复及有界审计恢复。当前仅允许对 CAL-WORD-PARAGRAPH-001 的发送前 CDP 配置失败恢复一次，
不增加模型次数、120秒预算，不重放 CAL-WPF-001。新增 scoped recovery 检查原失败/状态摘要、未消费
身份、无 pending/未决 ACCEPTED、真实契约 gate；只追加审计并变更 ERROR→WAITING_FOR_GPT，
不改链值或发送。job 保留完整失败快照并给一次重派权限。20 项针对性测试通过；本轮继续同一身份。
下方“等待用户决定／不允许 recover”等为历史规则，不能覆盖此最新授权；安全边界仍保留。

**本轮最新停止（root 已完成，派发入口失败）**：用户已完成 `CAL-WORD-PARAGRAPH-001` 的 root
安装/登记/真实 gate；自动接力初报生成并进入当前聊天，当前聊天写回 execute_contract 后，正式 Bridge
在首次 Chrome 读取前因缺 `BU_CDP_URL=http://127.0.0.1:9333` 返回 READ_FAILED。
job `CAL-WORD-PARAGRAPH-001-AUTO` 已 HUMAN_REQUIRED 并确认收到失败回报；没有发送控制请求、
没有启动 Hermes、没有新业务修改或宿主验收。journal 只有新增 READ_FAILED，新任务身份未消费；
Bridge 当前 ERROR／seq19／last_task_id=CAL-WPF-001／pending=false，不能当仍 WAITING_FOR_GPT。

源码已补齐正式 adapter 所需环境，并将不匹配端点/BU_CDP_WS 提前拒绝在状态修改之前；16 项针对性
测试通过。未做真实重试、recover、直接改 state 或创建替代身份。值得继续的依据是明确的入口接线
缺陷；但现有 recover-preconsume 只覆盖 CONTRACT_REJECTED，不覆盖本次 READ_FAILED。
下一步须先由用户决定继续与可信恢复范围，不能绕过该失败门禁；不能用“身份尚未消费”自动再发一次。
以下准备记录为历史过程，不再表示当前仍缺 root。

**当前用户新要求：回到日历真实开发验证。** 用户已明确要求“通过系统开发日历 → 汇报自动到当前
本地 Codex 界面 → 审查指令自动交回系统继续”，不是再做只读演示。本轮据此准备一个新的、有价值的
小切片 `CAL-WORD-PARAGRAPH-001`：Word body-level 段落导入，仅导入器和测试，不含表格/UI/依赖。
这是当前明确用户要求下的新范围；旧 CAL-WPF-001 仍 FAILED/124 且已消费，不重放、不 recover。

- 批准工作副本：`/var/tmp/RILI-WPF-V2/WORD-PARAGRAPH-001/project`，HEAD
  `59f9b807a3516740fff9bf8784221b534f70bf44`。正式 main 保持 `832836e`；本轮只提交了项目拥有的
  8 份作者输入，没有业务实现或测试代码。契约五门 PASS／READY／errors=0，manifest
  `b451b36ce9d4083d584b0b7af3f69a173f3c3f8e4275d17551fbd28d32d9c291`。
- 真实自动接力 job `CAL-WORD-PARAGRAPH-001-AUTO` 已冻结并提交，当前 WAITING_PREPARATION。
  精确任务预算 120 秒、清理宽限沿用 10 秒，失败不重试。宿主验收使用已有 SDK 与
  `FullyQualifiedName~WordParagraphImportTests`，要求真实执行 >=4 项且全通过，并审查实际差异/断言。
- 唯一当前阻断：新任务尚未 root 安装/登记；registry 与 trusted 目录 root 拥有，当前不可写。
  现有 `aegl/recovery/calendar_wpf_001/prepare.sh` 增加 `--task` 数据参数复用，不复制准备设施；
  修正 worktree Git 元数据路径为实际查询结果。新任务 `--check` 已通过，脚本 SHA-256
  `e7c9cdd29ab219d342893a42e3a5024b744aa13e5aa89ea245f615d4d9b5dddb`。
- 队列新增 WAITING_PREPARATION：登记缺失时只读等待，不调用模型或发送；真实登记和 gate 通过后自动
  开始汇报、当前聊天审查、一次原 Bridge/Hermes 执行、结果回传与宿主验收。相关 15 项测试通过。
  heartbeat 提示已更新到该精确范围，不再把本轮视为“缺新执行授权”；授权已有，缺的是 root 权限操作。
- 当前状态仍为业务/模型执行/宿主验收 NOT_RUN；没有 root 执行、Chrome 发送或新 round。
  用户执行一次已审查的 root 准备命令后，后台在同一冻结 job 中自动续行，无需再搬运汇报或重复申请
  同一单次授权。该 job 总等待/接力窗口 1 小时，若超时则停手，不自动延长或另建身份。

**第二阶段（本轮）**：用户进一步明确要求继续接通业务派发、后台运行与当前聊天。
新增 `agent_link_jobs.py`／`agent_link_actions.py`；业务派发通过原 Bridge，新的 entry guard
在锁内、启动恢复或状态修改前拒绝未授权／已消费身份。dotnet 宿主验收采用外部副本、只读宿主
沙箱和真实 TRX 非零测试计数。14 项新增测试通过（含真实 Bubblewrap 写入边界）；真实 CAL-WPF-001 预检查被
`TASK_ALREADY_CONSUMED_NO_RETRY` 拒绝，未触发 gate／Chrome／round，Bridge state/journal 不变。

当前聊天直连使用正式 `codex queue`，不需要打开 control socket。nonce 探针及本地自动汇报
已实际进入当前聊天；receipt 位于外部 state 的 `agent-link/current-chat-probe.json`。
当前接力任务 `STACK-CURRENT-CHAT-AUTO-20261121` 的 plan 中 `task=null`，只授权核对原失败报告一次，
两份本地回报均通过正式 queue 实际到达本聊天，本聊天已审查、写回一次核对指令并最终决定 COMPLETE。
源报告哈希与权限未变，初报中“清理／回传”的标签也经核对纠正；没有人工复制粘贴。
旧回报哈希去重，不重复派发。当前 job 已 COMPLETE，只有一次 inspect_evidence，没有业务执行。

应用 heartbeat “Stack 当前聊天自动接力”（ID `stack`）已 ACTIVE，每分钟检查当前聊天队列。
无变化保持安静；只推进冻结范围内且确有用户授权的动作。应用和电脑需运行，不声称 OS 开机常驻。
首个系统 heartbeat 已于 2026-11-21 08:49（Asia/Shanghai）实际到达并完成队列读取，待办为 0；
这证明后台唤醒与当前聊天回调，不代表后台消费过业务动作。用户停止时可暂停 heartbeat
或请求 `stop` 阻止下一动作；已开始的受控步骤沿用原预算和清理，不强杀特权监督进程。

业务动作代码与离线门禁已经接入；**没有新鲜、未消费的业务单次执行授权，故新业务成功实证与
真实 dotnet 业务验收本轮 NOT_RUN**。不得用本次接入授权重跑 CAL-WPF-001、生成 CAL-WPF-002，
或将普通会话开发当系统成功。源码仍只在批准 Stack 开发副本，未正式晋升或 root 安装。
以下条目保留上一轮独立会话通信基线，不能将其中“尚未接通”的历史描述当作本轮新状态。

- 用户已完成 CAL-WPF-001 的 root 准备；单次真实业务任务随后 BLOCKED / exit 124（120 秒超时），
  清理和回传确认。无业务改动、WordImportTests 0 匹配，业务验收 FAILED，根因 SYS-09 UNKNOWN；
  Bridge 已推进到 seq 19。不得再把 root 登记当作本项目当前阻断，也不得自动重跑或创建 CAL-WPF-002。
- 用户明确转向建设“本地 AI 自动汇报 → Codex 审查 → 自动接收指令与回报”的能力，并接受先使用
  独立 Codex 审查会话。本轮在批准 Stack 开发副本实现只读最小版本
  `orchestration/hermes/supervisor/agent_link.py` 和项目拥有的工具禁用 mod。
- Codex 默认 control socket 不存在；未尝试绕用桌面内部 IPC，也未改配置开放接口。独立审查通过
  官方 App Server stdio；本地端为 Command Code 1.91.1，沿用 DeepSeek 模型，在新通信会话中运行，
  没有接管原交互进程或并行修改其业务文件。
- 真实自动往返已 COMPLETE：通信 `STACK-REPORT-LINK-FORMAT-FIX-20261121`，
  Codex 会话 `01a1fb78-0ec7-7320-8253-8e21ee691917`（“Stack 自动审查：报告通信验证”），
  Command Code 会话 `06e0ba1d-9902-4cb1-9c83-e9289fc195ef`。四条关联消息，一次固定报告读取；
  14 项边界测试及独立核对 PASS。首次通信因本地回报 JSON 不合规而停止，模板修正后才通过，
  不是 CAL-WPF-001 业务重试；未新增 Bridge 任务、未消费新序号。
- 当前只允许 `inspect_evidence`，不能将模型文本直接作为 shell 执行；它尚未接入自动业务动作、
  后台常驻、原交互会话接管或当前桌面聊天直连。不得把本次通信成功写成业务成功或通用接入完成。
- 运行记录在 Stack 外部 state 的 `supervisor/agent-link/<通信ID>/state.json`；源码与文档在
  批准开发副本，未晋升正式树、未可信安装。下一方向是复用这条通道接入明确授权的既有受控动作，
  保留原契约／安装／沙箱／失败门禁；不以通信改造为由重开 005 或扩建诊断。

- 业务目标：Windows 离线任务日历 WPF V2，C#／WPF／.NET 10；保留旧版功能，按六张 UI 图实现。任务包：`/home/zhong/EXE/RILI/DeepSeek_WPF_TaskCalendar_V2`。
- 正式业务仓：`/home/zhong/EXE/OfflineTaskCalendar_WPF`；批准 worktree：`/var/tmp/RILI-WPF-V2/CAL-001/project`；运行产物：`/home/zhong/EXE/RILI/artifacts`。
- Stack 开发副本：`/var/tmp/IAP-CONTROL-DEV/stack`；AEGL 开发副本：`/var/tmp/IAP-CONTROL-DEV/aegl`。不要修改正式系统仓或未跟踪的旧 004 文件。
- 业务报告声称 83 项测试和 Linux 交叉构建完成；Windows 图形、托盘、通知等未实机验证。本次交接未重跑其测试，不把交叉构建当 Windows PASS。
- 只读审查发现：日历 binding 与 Git 归属检查已做，但作者输入／可信安装／登记／受控执行未完成；业务文档明确承认由普通会话直接编码。已有成果可保留，但不能补标为系统受控开发。
- 审查时 Bridge 最后任务仍为 SYSTEM-E2E-005、下一序号18、44条 journal、无日历匹配、无 pending。本项目 Chrome 自动咨询无可核验关联证据。历史快照不可用来重置状态或证明当前状态。
- 审查时正式业务仓832836e、CAL-001 worktree3b05f6f；未取得可信晋升记录，不据此推断每次编辑的位置。
- 旧台账“无新增系统缺陷”已补充纠正：受控链路 NOT_RUN 不等于系统无缺陷。新项目接入阻断和转为直接开发的流程偏离须分别记录；不把所有权限限制叫代码 bug。

## 接下来怎样继续

DeepSeek 的 CAL-WPF-001 失败报告已回传，任务已停止。当前用户选择的工作是上节自动汇报通道；
新对话先核对最新回传、仓状态和其他执行者进度，不重复安装、发送、登记或执行，不并发修改同一文件。

当前优先：收口已经通过的只读自动汇报验证，保留 CAL-WPF-001 失败与 UNKNOWN；后续只按用户选择
接入已有可信动作或处理有价值的实际阻断。Word 导入尚未实现，不自动再发一轮。

此后判断能否把接入流程用于其他授权项目：本项目成功不代表通用化完成；通用化不能变成脱离真实业务的基础设施扩建。

本对话主要为用户审查结果、给 DeepSeek 指令。新对话未经用户新的明确要求，不接管另一执行者的开发，不自行发送 Chrome 消息或运行真实任务。用户已有授权可延续，但须核对适用对象、范围和是否已消费；文档本身不授予权限。

## 每轮汇报

分别报告业务结果、系统闭环结果、设备实机结果；列出实际系统功能及证据位置、失败／UNKNOWN、必要修复、源码／安装／真实验证的不同状态、收口决定和下一业务方向。受控链路阻断时不得默默转普通会话开发；降级须在用户明确认可范围内。

每轮读取并更新同目录 `SYSTEM-VALIDATION-REVIEW.zh-CN.md`。总结是交付记录，不是新增门禁，不为补指标重跑已收口工作。
