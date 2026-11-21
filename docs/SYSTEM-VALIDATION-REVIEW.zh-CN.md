# AEGL／Stack 业务验证方向与问题台账

更新日期：2026-11-21。适用系统：AI Engineering Governance Layer 与 Google Android Agent Development Stack。

本文回答三个问题：最近的真实任务证明了什么、系统还存在哪些实际问题、下一次业务应验证什么。它是人工维护的交付总结，不是新的测试、部署、诊断框架或执行门禁。系统名称不以 ImageAnalysisFactory 等某个业务项目代替。

## 1. 固定推进方向

1. 一次集中审查，只列真正阻止执行的问题；非关键完善项留后。
2. 用现有可信方式完成必要安装与准备，不再建设封包、部署或诊断框架。
3. 获得授权后，执行一次 120 秒真实任务并做独立验收。
4. 根据结果判断是否完成；失败保留真实证据。按 2026-11-21 最新用户授权，在既定范围内对原因明确且安全可证的故障自动修复、经有界审计恢复入口继续；不为绕过失败换身份、重放已消费任务或扩大预算。超范围、权限或证据不足仍停手。

**每项新增工作必须回答：它具体阻止了哪一步真实执行？回答不了，就不得成为新的前置条件。**

已通过且未变化的传输修复、测试清理、诊断提取保持收口。只有新的实际失败证据，或直接影响下一次执行的必要变更，才重新打开对应部分并集中说明原因。新对话、交接和上下文压缩不构成重开理由。

## 2. 每次任务怎样使用本文

### 跨项目自动接入的长期目标（2026-11-21 补充）

用户提供项目路径、需求与授权范围后，系统应复用现有入口和可信接口，自动串起精确 binding／Git 归属、项目契约五门、可信安装／登记／实际 gate、Hermes 沙箱执行、Chrome ChatGPT 指导、清理／回传／独立验收和系统问题总结。项目差异由项目拥有的需求与配置表达，不应每换项目就修改系统源码或复制专用设施。此为建设与验收目标，当前尚未证明通用自动接入已实现。

受控链路阻断后直接使用普通会话编码，不能算系统自动开发验证通过。业务结果、系统闭环结果、设备实机结果必须分开。继续遵循第 1 节收口原则，不以通用化为由新建部署、诊断或验证框架。最新交接与日历项目证据限制见 [SYSTEM-AUTOMATION-HANDOFF.zh-CN.md](SYSTEM-AUTOMATION-HANDOFF.zh-CN.md)。

- 开始前：读取最近结论和未关闭问题，从用户的实际业务目标中选一个明确任务，先写出产物和独立验收条件。不要把本文全部方向变成必须先跑完的清单。
- 完成或失败后：用第 7 节模板追加一条简短记录；更新问题台账的状态、证据和实际影响。没有新问题就写“无新增”，不要为凑总结发明缺陷。
- 修复后：分别记录源码提交、安装状态和真实任务证据。提交、安装、单个测试通过是不同事实，不相互代替。
- 失败后：保留真实退出码和失败历史；明确继续还是停止，以及继续的业务价值和修复依据。没有依据，不自动申请新任务试错。
- 交接时：携带当前结论、未关闭问题、用户选择的下一业务目标和停止条件。文档描述不授予 sudo、部署、发送、模型调用或真实执行权限。

总结不复制原始日志、聊天正文、凭据、完整链值、图片、数据库或运行产物进仓。只保留必要结论、任务标识、证据摘要及代码关联；临时证据路径不是永久存档承诺。

## 3. 当前收口基线：SYSTEM-E2E-005

### 已证明的范围

005 完成了固定控制会话中的请求发送、新控制块验证、受控契约编译任务、结果回传和独立宿主产物验收。它证明这条受控任务链路能够完成，**不代表全部业务能力、跨机部署或无人值守运行已经全面验收**。

| 项目 | 005 的结论 | 证据范围 |
|---|---|---|
| 请求发送 | PASS，单次 exact 确认 | 用户回传的执行报告记录 `CONFIRMED_SENT`、完整请求在用户消息中出现 |
| 控制器接受与结果 | SUCCESS / exit 0，sequence 17 | 已只读核对 Bridge journal 的 `ACCEPTED`、`RESULT`；不是由 CLI 退出 0 推断 |
| 任务预算 | 120 秒，清理宽限 10 秒 | 报告称约 60 秒内完成；没有延长预算 |
| 清理 | 执行报告为 PASS | 报告记录运行目录已清理、无残留；本次文档未重新执行检查，也不以目录缺失单独推断监督标记 |
| 结果回传 | PASS | 报告记录唯一 SUCCESS 结果块与 journal 摘要一致，链推进到 18、pending=false |
| 独立业务验收 | PASS，`ACCEPT=OK` | 8 authored members / 1 requirement / 1 task / READY / 0 errors；五门 PASS |
| 输入与辅助脚本 | PASS | 22 项声明输入、9 个 fixture 文件未变、5 个辅助脚本哈希匹配 |
| 工具恰好一次读取、一次执行 | UNKNOWN | 单次 round、文件数量和时间戳不能证明工具调用次数；本轮未提取工具级 sink |
| 真实失败时立即停止 | 本轮未实证 | 本轮任务成功；既有离线失败传播检查不冒充本轮发生过失败 |

固定 manifest：`c5cf4264e3311cb6b28fbb411de8fa049aca55b11c9bb40f8b0b6f643944e036`。

固定 prompt：`57eb8fd879f56f28cebae1ead1458b4addeedc8c1684c693518dd6b9fb7507cc`。

结果摘要：`86516d6792ad1bddeabd325eebd36f8a885665964dbd6d0cc1c711110375ce2f`。

来源：用户回传的 005 安装／准备与执行报告，以及本次交接期间已读取的 Bridge journal。sequence 18 等运行状态是该次报告快照，不是下次执行的实时状态或重置依据。旧 001—004 的失败结果保持不变，不回填为成功。

### 已生效的修复边界

| 部分 | 源码关联 | 已知生效范围 |
|---|---|---|
| 控制页 assistant 选择 | Stack `cf52c3595fcdd642041f1308f554cecfebcb775d` | 排除隐藏空候选的修正已用于 005；不承诺未来网页 DOM 不变化 |
| 传输等待与响应异常 | AEGL `4067c05f6b2fb2e4d10f724d7cedd3f0249e5ee1` | 已安装 broker `b9ff6a51…`、shim `40e71b3d…`；已完成直接相关离线验证，005 使用这些安装 pins |
| 测试生命周期清理 | AEGL `645bc73c7310ac489e25754f7a00130f29263cf8` | 既有针对性测试已收口，不为新交接重复运行 |
| 作者输入与可信准备 | AEGL `6513189f831fe622fa8cdce446a9ccf308a6b486`、`c3b45ea01184ef34e065ea6b9d650e02b647341b` | 内联代码移入只读、已声明且固定哈希的辅助脚本；005 安装、登记和实际 gate 已完成 |

这些修复不证明 004 两条历史工具错误均已确诊，也不证明 005 成功只能归因于某一项改动。后续不要为补这种历史因果证明而重跑已消费任务。

## 4. 系统问题台账

状态只表达证据：**已收口**、**待业务触发处理**、**UNKNOWN**。未覆盖的能力不自动算缺陷，非关键问题不自动升级为执行阻断。

| 编号 | 问题与状态 | 已有依据 | 对下一业务的影响与处理方向 |
|---|---|---|---|
| SYS-01 | 控制页误取隐藏空节点：已收口 | 真实页面定位、adapter 修复及 005 成功读取 | 无新失败不重开；若页面改变，先区分加载状态与选择器失效 |
| SYS-02 | shim 空闲断流／broker 已开始响应后追加 502：已收口 | 可复现的离线缺陷、修复、可信安装及 005 使用 | 不重跑传输套件；只有新失败直接指向该层才审查对应边界 |
| SYS-03 | 内联 heredoc／解释器 `-c` 与 single-query 默认 deny 不兼容：已收口于005方案 | 真实审批上下文的机制复现，以及 005 辅助脚本方案成功 | 新作者输入沿用可审查、声明哈希的只读脚本；不关闭审批、不使用自动批准 |
| SYS-04 | 浏览器／Harness 进程退出及环境未就绪：待业务触发处理 | 多次发送前遇到 9333 不监听或 daemon 不在运行；005 经授权恢复成功 | 仅在下次实际发送前不就绪时阻断；可在当次授权中包含必要的一次恢复。无明确无人值守业务需求，不建设自启或监控服务 |
| SYS-05 | 005 精确工具调用次数缺少本次提取证据：UNKNOWN | journal 证明一次受控任务，不证明内部工具次数 | 当前不阻止已通过的产物验收、不补跑。未来若业务明确要求次数证明，优先只读使用已有 sink，不先新增采集字段 |
| SYS-06 | 004 原始工具错误全文及实际 executor 上下文不完整：UNKNOWN | 两条 hook 记录快速 `exit=-1`；模型 `timeout=300` 已提取；原始 tool result 未持久化 | 保留历史限制，不继续猜测性改 timeout/cwd，不以新任务补写旧证据。新的真实故障再按其证据处理 |
| SYS-07 | 新业务受控接入缺少 root 契约安装/登记能力：已收口 | 用户执行 root 准备成功；registry 条目、trusted manifest、worktree owner、BASE_COMMIT 已核对 | 不再阻断 CAL-WPF-001；保留为其他新项目接入的前置说明 |
| SYS-08 | 前阶段业务代码由当前会话直接提交正式仓，偏离受控闭环：已记录并纠正 | 正式仓 `main` `d362963`…`832836e` 为会话直接提交；journal 无日历任务记录 | 保留成果但不回填为 Hermes 结果；正式仓只读，新工作只在 CAL-001 worktree，交付走可信晋升 |
| SYS-09 | CAL-WPF-001 单次受控执行 120 秒超时且 worktree 无变更：UNKNOWN | round `BLOCKED`/exit 124/timed_out；cleanup CONFIRMED；result CONFIRMED_SENT；worktree status 空；无任务级诊断（不在 launcher 白名单），scratch aegl-ai 750 不可读 | 阻断该业务任务；不重跑、不 recover。已定位一个契约层缺陷（SYS-20），但超时根因仍无工具级证据 |
| SYS-20 | CAL-WPF-001 契约 `read_first` 路径与 sandbox cwd 不一致：已定位，已在 CAL-WPF-002 修复 | bwrap `--chdir <worktree>`；契约写 `project/src/...`，从 worktree 读取为 `project/project/...`；`test -f` 实测前者存在、后者不存在 | 使模型无法按指令读取既有 API；是否为超时直接原因仍 UNKNOWN。CAL-WPF-002 已改为绝对路径并 READY |
| SYS-10 | 自动汇报接口首次本地回报 JSON 不合规：已修复并验证 | 首次通信在严格解析处停止，未派发动作；分离输出模板与输入数据后，真实四消息往返 COMPLETE；14 项边界测试通过 | 只读报告审查已接通；不据此声称业务执行、当前桌面直连或通用自动接入通过 |
| SYS-11 | 自动派发未声明正式 Chrome adapter 环境：已修复并真实验证 | 首次读取前 READ_FAILED；固定正式端点并拒绝冲突。用户授权后经 INITIAL_READ_RECOVERY 审计继续，实际控制发送及 ACCEPTED 成功 | 入口问题收口；原失败保留，不把后续业务超时归因于此 |
| SYS-12 | Hermes bootstrap re-exec 丢失项目入口导入路径：已修复并真实验证 | 原重启 ModuleNotFoundError，未发送未消费；运行时选择提前且显式入口路径。23项针对性测试PASS，精确请求只读确认不存在后经 BOOTSTRAP_READ_CONTINUATION 续接同次尝试，实际进入EXECUTING | 已收口；未增加模型次数或任务预算。CAL-WORD-PARAGRAPH-001后续120秒超时根因仍UNKNOWN，与SYS-09同类现象但不能推定同一原因 |
| SYS-13 | 桌面NNP子进程承担需要sudo的宿主执行：已修复，宿主真实入口验证通过 | 用户启动HOST-001的host-run，seq21真实受控执行；摘要确认sandbox准备、模型响应及工具事件，固定summary读取exit0 | 入口阻断收口；业务随后120秒超时，无代码，不能将入口通过当业务通过。不清NNP或自动拉起外部进程绕过 |
| SYS-14 | 结果停在composer，Enter未完成提交：已修复并真实验证 | 完整616字符canonical仍为草稿，用户turn无该结果，同form唯一可用发送按钮存在。改物理单击且保留exact确认；用户明确授权一次补发后原resolver真实CONFIRMED_SENT，resend_count=1 | Bridge WAITING_FOR_GPT/seq21/pending=false，回传阻断收口；FAILED/1原业务结果不变，未重跑Hermes。证据send-resolution.json及journal |
| SYS-15 | 普通宿主PATH无codex，初报通知未启动却误标发送不确定：已修复，原报告通知已恢复 | 初报6918a73e…保留；CLI绝对定位、NOT_SENT区分及精确恢复，36项测试通过，普通终端类似环境真实QUEUED且new_model_call=false；用户重启后HOST-001已实际执行并自动回报失败 | 通知入口收口，不重复root/报告生成/恢复；本轮业务超时另记SYS-16。真正不确定发送不适用此恢复 |
| SYS-19 | CURSOR-004 受控闭环业务验收通过（write-first+300s） | Hermes SUCCESS/0 seq24；host WordParagraphImportTests executed=6/passed=6；job COMPLETE；控制块作废说明与 recover-control-differs 已用 | 业务源码仅在 disposable worktree；正式 main 仍 832836e；Windows NOT_RUN；晋升需另授 |
| SYS-18 | 连续超时几乎无写盘：提示前载探路；已改为 write-first+绝对包路径；CURSOR-004 300s | CURSOR-003：read/terminal 多、write_file=0；HOST guard CWD_RELATIVE 探包。build_contract 硬顺序写后验；计划预算允许120/300 | 系统修复≠业务通过；待 root prepare+host-run CURSOR-004 |
| SYS-17 | CURSOR-001 CONTROL_DIFFERS 卡死 Bridge ERROR：已审计恢复；CURSOR-002 冻结 | seq23 发送后控制块不一致、无 ACCEPTED；`recover-control-differs` 单测通过并已授权恢复；CURSOR-002 check PASS，thread_id=cursor-inbox | 系统恢复不等于业务通过；待 root prepare+host-run；旧失败身份不重放 |
| SYS-16 | HOST-001 超时无业务改动：路径交接已加强为绝对路径提示，完整超时根因仍UNKNOWN；修复后真实开发待 ABS-001 | 工具4次ERROR/16次OK；11条guard请求rc0且反复相对名/find/ls。生成器现烘焙绝对 source_root/read_first 与 `$HERMES_CONTRACT_PACKAGE/...`，13项相关检查通过；Stack `1677f82`。新任务 CAL-WORD-PARAGRAPH-ABS-001 已冻结 WAITING_PREPARATION，旧身份不重放 | 阻断已消费 HOST-001；下一验证走 ABS-001 单次120秒+宿主>=4项测试。未获 PREP_COMPLETE 前不调用模型；不能把源码修复说成业务通过 |

问题如有状态变化，在此表更新，并在任务记录中留下变化依据。业务已完成而问题仍 UNKNOWN 时，可以保留 UNKNOWN；不要为了让整表变绿而重跑任务。

## 5. 下一次验证由实际业务选择

当前实际业务目标（2026-11-21 起）：**Windows 离线任务日历 WPF V2.0**
（业务仓 `/home/zhong/EXE/OfflineTaskCalendar_WPF`，开发 worktree
`/var/tmp/RILI-WPF-V2/CAL-001/project`）。当前选定受控任务为 `CAL-WPF-001`
Word `.docx` 导入；离线契约已 READY（manifest `639ed1fe…`），root 安装/登记已通过，
随后单次受控执行超时、业务验收 FAILED，根因 UNKNOWN，见第 8 节。
用户随后选择建设自动汇报与审查通道，最小只读往返已通过；业务任务保持停止。
**不预创建 006，不把再次执行同一编译 fixture 当作默认下一目标。**

| 用户真正需要的工作 | 本轮应回答的问题 | 可独立判断的验收例子 |
|---|---|---|
| 某个应用的一项小功能或缺陷修复 | 能否把具体需求变成正确、范围受控的代码变更？ | 目标行为达成、相关回归通过；需要设备时按该业务的确定性设备路径验收 |
| 一组真实输入的处理 | 能否产出内容正确、来源对应的结果？ | 样本与结果关联、实际内容正确、原输入未变；仅模型退出 0 不算通过 |
| 已遇到的真实失败 | 能否准确停手、保留证据并在有依据时修复？ | 真实错误未掩盖、清理可确认、未越权或重发；是否再执行由用户明确决定 |
| 实际交接或后续维护 | 新会话能否继续业务而不重开已完成阶段？ | 依据最新记录正确识别源码、安装与运行状态，沿现有路径完成用户要求 |

每轮只选择与当前目标有关的一项，不同时铺开全部方向。先写清业务验收，再选必要验证；不要先扩建验证工具再寻找用途。原有 P0/P1、r10 等结论继续按各自证据范围保留，不因本文未重述细节而重新测试。

## 6. 继续还是停止

- **任务及独立验收通过**：收口该任务，记录残余限制；等待用户下一实际业务目标。
- **缺少一个明确执行前提**：只处理这个真实阻断，优先把必要恢复纳入一个完整授权范围，不拆成反复中转。
- **失败且已有具体可修复依据**：集中说明问题、修复和恢复范围；在既有授权与预算内自主修复并经有界审计入口继续，仅超出原范围才申请新增授权。不重放已消费身份或盲目重发。
- **失败原因仍不足以定位**：保留 UNKNOWN，说明现有证据能回答什么；与用户判断继续的价值，不自动创建下一任务或诊断基础设施。

“整套系统已完善”不是由一次 PASS 得出的结论。应逐步说明：哪些实际业务已验证、哪些实际问题已解决、哪些能力尚未覆盖；避免给出没有依据的完成百分比。

## 7. 每次任务结束后的最小汇报模板

复制本节格式，在第 8 节追加一条即可；不要求另建报告文件或自动化。

```text
日期／任务／业务目标：
预先约定的独立验收：
实际结果：发送；任务outcome/exit；清理；回传；独立验收。
已证明的范围／证据摘要：
本轮系统问题：编号；新增/已解决/未解决/UNKNOWN；实际业务影响。
修复生效位置：源码提交；是否安装；是否已有真实验证。
未覆盖或无法证明的部分：
收口决定：完成/停止/有依据地继续；原因。
下一步：用户选择的业务目标或必要动作；需要的授权；明确不自动做什么。
```

## 8. 简短任务记录

### 2026-11-21 CAL-WPF-001 失败定位与 CAL-WPF-002 准备

- **失败定位**：只读核对确认 bwrap 以 worktree 为 cwd（`--chdir <worktree>`），而
  CAL-WPF-001 的 `read_first` 写成 `project/src/...`；从 worktree 读取会变成
  `project/project/...`，实测不存在。该契约层缺陷已定位；是否为 120 秒超时的
  直接原因仍 UNKNOWN（无任务级工具证据）。没有重跑 CAL-WPF-001。
- **新任务准备**：新建隔离 worktree `/var/tmp/RILI-WPF-V2/CAL-002/project`
  （分支 `CAL-002`，基线 `832836e`），作者输入提交为 `3d9a87d`；
  `read_first` 改为绝对路径，契约 READY、五门 PASS、errors=0，
  manifest `b1e08ba6fc69578a6c9b86ab38fce07071df1284de7187527ac42860ad7a86e1`。
- **只读核验**：使用现有参数化入口
  `recovery/calendar_wpf_001/prepare.sh --task CAL-WPF-002 ... --check`
  通过，输出 `BINDING_OK` / `CHECK_OK`。
- **系统问题变化**：新增 SYS-20（契约路径与 cwd 不一致，已在新任务修复）；
  SYS-09 保留 UNKNOWN；SYS-07 已收口；无新增系统代码缺陷。
- **修复生效位置**：AEGL 开发副本提交 wrapper 哈希 pin；未做 root 安装/登记。
- **未覆盖**：CAL-WPF-002 的 trusted install、register、gate、launcher、Hermes、
  宿主验收全部 NOT_RUN；Windows 实机 NOT_RUN。
- **收口决定**：在唯一 root 外部阻断处停止；不重跑 CAL-WPF-001，不自动执行
  CAL-WPF-002，等待一次经审查的 root 准备命令。
- **下一步**：用户执行 CAL-WPF-002 的 root 准备；成功后再重新读取 Bridge 链值、
  单次发送唯一控制块并执行一次 round。

```text
日期／任务／业务目标：2026-11-21／CAL-WPF-001 失败定位＋CAL-WPF-002 离线准备／Word docx 导入
预先约定的独立验收：CAL-WPF-002 契约 READY；round 后宿主 WordImportTests >0 全通过；源哈希不变
实际结果：CAL-WPF-001 BLOCKED/124；无重跑；CAL-WPF-002 --check CHECK_OK；无 root 准备
已证明的范围／证据摘要：read_first 路径不匹配实测；CAL-002 manifest b1e08ba6…；worktree 3d9a87d
本轮系统问题：SYS-20 已定位并修复于新契约；SYS-09 仍 UNKNOWN；SYS-07 已收口
修复生效位置：AEGL wrapper hash pin；CAL-002 契约输入；未 root 安装
未覆盖或无法证明的部分：超时根因；CAL-002 trusted install/register/gate/round/宿主验收；Windows
收口决定：停在 root 外部阻断，不自动执行新任务
下一步：用户执行 CAL-002 root 准备；成功后发送控制块并 round 一次
```

### 2026-11-21 ABS-001 准备：绝对路径提示加强，等待 root

日期／任务／业务目标：CAL-WORD-PARAGRAPH-ABS-001；验证 SYS-16 绝对路径提示修复后的 Word 段落导入。
预先约定的独立验收：宿主 WordParagraphImportTests 实际执行 >=4 且全通过；源码差异与断言核对；Windows NOT_RUN。
实际结果：发送／执行／清理／回传／独立验收均 NOT_RUN。离线：契约 READY、`--check` PASS、job WAITING_PREPARATION。
已证明的范围／证据摘要：Stack `1677f82` 烘焙绝对 source_root/read_first 与 `$HERMES_CONTRACT_PACKAGE/...`；13 项相关检查通过；manifest `96d144ec…`；plan `6774ea93…`。
本轮系统问题：SYS-16 源码加强，修复后真实开发仍待本任务；完整 HOST-001 超时因果仍 UNKNOWN。
修复生效位置：Stack 源码已提交；可信安装／登记 NOT_RUN；真实验证 NOT_RUN。
未覆盖：Hermes 执行、业务产物、宿主验收、Windows。
收口决定：有依据地继续；停在用户 root 认证前。
下一步：用户执行已交付的 prepare+host-run；本会话 decide/ack；旧四个失败身份不重放。

### 2026-11-21 HOST-001 真实执行：超时，自动回报已接收

- **guard核对与修复收口**：用户只读请求提取exit0/stderr空，输出SHA
  `794007fa623220f3c4dd7f3ade2551bf54b9cb2c5a1876624d00a8dcf225e65f`；capture SHA
  `cf770cb02da82e326a829cada5a934880c072b5284fc7ea2d308f7c4c527a27a`。11条相关请求全记录、rc0，
  未显式传workdir；6条含find词、7条含ls词，多次契约相对名，无逐字匹配冻结CLI命令的hash。
  这些为词法提示，不据此重构完整命令/内部cwd；guard ALLOW无stdout是原协议，不另改guard。
  提示路径交接缺失已静态证明，实际查找行为支持其影响；完整超时因果、4条错误具体正文仍UNKNOWN。
  原提示生成器已补包目录/源码根/CLI cwd，并给一次只读printf取路径和批量读取指引。独立启动cwd
  回归及相关CLI9/build3共12项通过；旧冻结包、身份、预算不改，无新模型调用。
  查因提取到此收口，修复仅源码/离线验证完成，真实开发效果NOT_RUN。业务仍FAILED，宿主验收及
  Windows NOT_RUN；不重复提取、扩诊断设施或自建下一任务。
- **工具结果实证及必要修复**：用户认证只读提取成功，exit0/stderr空；新摘要SHA
  `1f82794897256d052fb6739082c85bd794bcc43676fa7432c3185672590a69f6`。20个post有4个ERROR：
  terminal三次exit1/2/1、read_file一次；其余16个OK，无write_file/patch事件。不能据此断言terminal
  是否尝试写入。静态确认启动cwd与提示包文件/源码相对路径基准不同，直接按cwd解析均不存在；
  提示生成器已明确HERMES_CONTRACT_PACKAGE、source_root及登记CLI cwd，11项既有相关检查通过。
  未修改旧冻结包；此确定缺口与本轮4个错误的因果仍UNKNOWN，不能说完整根因已修好。
  复用现有guard请求字段提取器，精确registry绑定--task，固定类别/命令hash/声明文件基准提示输出，
  3项检查通过；源码SHA `83b5744de11095d1b4b30e6154b0ea6f3cad6ae39f1037d9fe5ff82ad6ca4cbd`。
  待普通终端认证读取已有guard-capture，落盘guard-request-summary.json并自动回执；不调模型/重跑。
- **继续查因（用户随后要求）**：确认broker已采集工具固定状态/错误类别/退出码/耗时，旧summary
  未输出这些字段，导致现摘要不能判断工具是否成功。仅修正现有AEGL摘要器的严格固定格式解析，
  10项相关检查通过，源码SHA `26f1cbbb937c582a793abec01540cd3a7222c0d89b99bc2ac2707780fc5d21bf`；
  prepare同步新版pin并精确接受已安装前版，未执行安装。新摘要不导出命令/正文/凭据，不改变采集、
  沙箱或工具门禁。本桌面NoNewPrivs=1，尚不能读取root/700原sink；需用户普通终端进行一次
  校验源码字节哈希的只读提取，输出`phase-summary-tools.txt`。原超时根因仍UNKNOWN，不声称已修好业务。
- **授权与实际结果**：用户普通终端重启已冻结host-run，自动取已审核execute_contract；seq21
  ACCEPTED后单次120秒BLOCKED/exit124，timed_out=true，清理CONFIRMED，结果CONFIRMED_SENT。
  结果SHA `cea206120c0eac532b476e3f79236d60bca451168d3c51e4aa6988cc90b0a345`；Bridge现
  WAITING_FOR_GPT/seq22/pending=false。失败report `c7b57f1439d6187ece2d42a738d26f57bec2adafaef487efc4652383152e4877`
  已由当前聊天ack，job HUMAN_REQUIRED，未下发host_acceptance。
- **业务**：worktree HEAD仍f18b30f，git status为空；WordParagraphImporter.cs与WordParagraphImportTests.cs
  均不存在。业务FAILED，无新增实现；宿主独立业务验收NOT_RUN，Windows NOT_RUN。正式main仍832836e。
- **系统已证明范围**：宿主执行入口、受控执行/清理/结果回传及当前聊天接收已发生；宿主按既有固定
  wrapper读取阶段摘要一次成功，exit0，摘要SHA `58360e87578a1523a4fc50bd3b4ba5453e8a2ce71716bc53ee669ea6f936716d`。
  308条元数据含sandbox准备/启动请求、14次完整模型响应、20对工具pre/post、11次guard返回0。
  第15次请求最后记录HTTP200响应头，无body完成事件；这些计数不是新增Hermes执行授权。
- **根因边界**：SYS-13宿主入口真实验证收口；新增SYS-16 UNKNOWN。当前summary丢弃arg内工具状态、
  错误类别、命令退出码和耗时，scratch无读取权限；不能认定20次工具成功，也不能确诊无代码的原因。
  不推定最后未完成响应就是根因，不回填旧任务。自动回报/审查通道接通不等于自动业务开发验收通过。
- **收口/下一步**：本轮失败停止，身份与120秒预算已消费；不重放、延长、另建替代任务或直接会话补代码。
  后续仅在既有权限和证据内查明工具执行无产物原因；不自动建设新诊断设施。

### 2026-11-21 HOST-001 初报通知入口修复与同报告恢复

- **实际状态**：用户root准备成功，组件REUSED、registry/gate/PREP_COMPLETE通过，三安装SHA匹配。
  普通宿主生成了正确初报，随后因PATH找不到codex在通知进程启动前ENOENT，host-run返回HUMAN_REQUIRED。
  初报6918a73e…保留，actions_done空、results空，Bridge seq21/pending=false；未消耗业务身份/120秒。
- **必要修复**：原入口解析显式/应用环境/PATH/既有桌面安装CLI位置，宿主在报告模型前验证依赖。
  启动前失败区分NOT_SENT并保留报告；新增精确有界通知恢复，核对初报hash、源hash、未消费/gate、
  期限与一次额度，保留失败，不直接改state，不重新报告模型调用；真正SEND_UNCERTAIN不自动重试。
  宿主在原窗口可以等待此类安全恢复。36项相关测试通过；实际clean环境queue帮助验证通过。
- **真实恢复**：按用户已有安全故障恢复授权，recover-notification-start复用同一已校验REPORT，在无
  CODEX环境的普通终端类似环境用官方绝对CLI真实QUEUED；new_model_call=false。原ENOENT快照保留。
  当前聊天复核真实安装/manifest和原人类授权后decide execute_contract，状态READY，仍无动作消费。
- **下一步与限制**：原宿主进程已经退出，只需普通终端重启同job的host-run；不重复root准备，不新建
  身份/契约/预算，不在桌面绕过NNP。当前业务/宿主业务验收/Windows NOT_RUN，不能称真实开发已完成。

### 2026-11-21 新授权修复后真实开发：CAL-WORD-PARAGRAPH-HOST-001 准备

- **授权/范围**：用户明确要求开始修复后的真实开发验证，新task/job分别CAL-WORD-PARAGRAPH-HOST-001
  和CAL-WORD-PARAGRAPH-HOST-001-AUTO；只Word段落导入器+>=4项测试，120秒/清理10秒，不重放旧3身份。
- **项目准备**：新批准worktree基于832836e，仅作者契约提交f18b30f；8份输入经现有三入口READY，五门
  PASS/0错。manifest f93a9583154d5cd6e6be9f73a90aeb809ecaff123b2ee85b9cd13c3a463158f3。
  计划hash825c0bec…已冻结submit，WAITING_PREPARATION，actions_done空；正式main未修改。
- **集中必要修正**：旧prepare硬编码升级前哈希，直接阻止本轮复用已安装诊断组件。改为launcher代码
  字节固定、任务配置行严格语法/原基线/已登记约束且拒绝其他改动；当前可信wrapper/summary直接复用，
  保留root归属/mode及sink不存在检查。5项针对性检查和本轮--check通过，未重跑未变化的61项检查。
- **真实状态与下一步**：root仍未运行，sink状态UNKNOWN；没有模型调用、控制发送、业务实现或宿主
  验收，Windows NOT_RUN。交付一次普通终端组合命令，root prepare成功后以普通用户启动绑定计划的
  host-run，由宿主取当前聊天审核决定自动执行、回报和独立验收；桌面不再承担sudo调用。
  本轮已有单次执行授权，缺物理root认证和用户显式启动；不重复申请或将新准备说成业务通过。

### 2026-11-21 用户普通终端宿主核验通过

- **实际文件**：host-context-check.json，SHA
  `8ccb13e2be7bd825bdde63f46b37bd0b155a2a4f0c6eefd66ffdcf51c05acf33`。
  返回host_context=READY、execution_attempted=false；job绑定正确，status=HUMAN_REQUIRED保留旧失败状态。
- **准确结论**：宿主只读权限前提/绑定核验通过，无模型调用、业务重跑或任务状态变更。SYS-13源码和
  环境层核验通过，真实业务层仍未完成；SYS-14回传已实证收口。Bridge WAITING_FOR_GPT/seq21/pending=false。
- **下一方向**：不再追加只读环境核验；在正常宿主进程按新的适用执行授权/未消费身份完成真实开发和
  独立测试，才可报告整链业务成功。当前日历无新实现，宿主业务验收/Windows NOT_RUN，三个失败身份不重放。

### 2026-11-21 根因修复：结果提交已实证，宿主执行归属已修改

- **回传现场与修复**：只读比对确认616字符完整结果仍在composer，用户turn无result，焦点在editor，
  同form唯一enabled发送submit存在。原Enter方式未完成提交；adapter改为唯一可用发送按钮物理单击，
  仍校验完整草稿及exact canonical用户turn；异常不重试，不用草稿当送达。4项提交检查及相关26项
  现有发送/确认/resolver检查通过。旧normal-path测试stub适配现有task_id关键字，断言未放宽。
- **真实单次恢复**：用户明确授权仅补发33b66caf失败结果一次。原resolver先持久化授权，单次发送后
  CONFIRMED_SENT/HUMAN_RESEND_CONFIRMED，human_resend_count=1，RESULT保持FAILED/1。
  Bridge WAITING_FOR_GPT/seq21/pending=false，未执行Hermes/未重跑/未新建身份。SYS-14收口。
- **执行归属根因**：实测进程祖先链为桌面主进程NNP0→桌面子进程NNP1→Codex1→shell1→python1。
  受限桌面子进程不能执行需要sudo的宿主动作；仅拦截错误不足以接通系统，需把执行交回授权宿主。
  不清NNP或自行通过外部进程逃逸。原任务stderr未保留，旧超时不据此回写根因。
- **已完成源码修复**：复用agent_link_jobs.py、step与worker锁新增单job host-run；显式绑定thread/plan
  hash和原deadline，拒绝root或受NNP限制的调用方。桌面只审查decide/ack，tick被NNP阻断时不改变
  READY任务，宿主正常用户进程取决定自动推进；阶段摘要在宿主内通过固定入口只读一次，不新建服务。
  31项队列/宿主测试通过，含终止job不重放、错绑定拒绝、状态不变、审查往返、单次固定摘要读取。
- **实际边界与下一步**：共61项相关检查通过。桌面真实--check-only已拒绝E_LAUNCH_NO_NEW_PRIVS且
  state字节不变；普通终端正向只读核验尚未执行。此核验不调模型/不跑业务，不是新一次任务授权。
  用户显式从普通终端启动宿主入口后，未来仅按新的适用授权和未消费身份执行，不回放当前三个失败身份。
  原业务FAILED、宿主业务验收/Windows NOT_RUN；自动回传修复不等于日历开发成功。

### 2026-11-21 普通终端阶段摘要读取结果（已收口）

- **自动接收**：用户执行固定只读summary后，直接读取stdout/stderr/exit三个项目外文件，无需复制
  内容。真实rc=2，stderr `DIAG_SUMMARY_FAILED reason=FileNotFoundError`（45字节），stdout为空。
  exit SHA `53c234e5e8472b6ac51c1ae1cab3fe06fad053beb8ebfd8977b010655bfdd3c3`，stderr SHA
  `4920df928214f8bc8e6170f7d2c3d9c903b713f14e21a63323058a23b5d58fd0`，stdout SHA e3b0c442…。
- **结论边界**：摘要所需诊断路径/文件未找到，不能写成成功读取到空事件集；未获得sandbox、模型或
  工具阶段证据。它与入口未正常启动的现象相符，但不能独立确定具体失败位置或回填前两轮超时原因。
  当前工具NoNewPrivs阻止必需sudo已另有直接证据；用户普通终端调用则已实际进入汇总器。
- **收口/下一方向**：诊断文件已消费记录，不重复请求命令，不再扩展诊断。需要允许既有wrapper的真实
  授权执行环境及对未确认回传的明确处理范围，不通过换进程绕过限制。当前queue无待办，业务FAILED、
  宿主验收/Windows NOT_RUN，SEND_UNCERTAIN/pending不变；未重发/resolve/重跑/另建身份。无新增代码问题。

### 2026-11-21 CAL-WORD-PARAGRAPH-DIAG-001 实际入口失败与权限阻断

- **准备与恢复**：用户root准备成功，安装三SHA/owner/mode及task白名单实际匹配。初次发送前9333
  refused，未发送未消费；专用profile无进程后按既有路径一次恢复Chrome/Harness，固定标签1个且
  已登录、无生成，精确控制请求不存在。扩展既有审计恢复只接受确切refused错误并拒绝任何发送
  记录，25项针对性检查通过。原失败报告f4046836…保留并ack，同任务/seq20/manifest/预算继续。
- **实际执行结果**：控制发送后ACCEPTED，受控入口FAILED/exit1，未超时，cleanup UNKNOWN。
  结果回传SEND_UNCERTAIN，result33b66caf…；独立只读canonical确认仍不存在，未重发/resolve。
  Bridge ERROR/seq20/pending=true；身份消费，job HUMAN_REQUIRED，report e940cb31…已ack。
- **业务/设备**：worktree status空，要求的导入器/测试均不存在。业务FAILED，宿主验收NOT_RUN，
  Windows NOT_RUN。Bridge的EXECUTING是控制器标签，缺独立证据证明Hermes业务进程/模型实际启动。
- **真实权限证据**：固定summary只尝试一次，sudo因NoNewPrivs拒绝提权（exit1），并未运行汇总器；
  本工具进程及父shellNoNewPrivs=1。当前通道不能进入必需root wrapper。原业务stderr未保留，
  不将此新诊断错误回填为当时业务日志；分阶段执行原因尚缺独立证据，旧超时根因也不据此回写。
- **必要修正与边界**：生产run_round增加发送/状态/消费前权限检查，3项检查验证阻断时无浏览器调用、
  无state/journal写入/消费；不更改NNP/权限，不通过外部进程绕过。源代码仅批准Stack副本。
  真实环境阻断未解除，不继续消费身份。新增SYS-13/14，已收口传输/隔离检查未重开。
- **证据与下一步**：项目外controlled/CAL-WORD-PARAGRAPH-DIAG-001下保留结果、诊断尝试及错误、
  进程权限和只读回传确认。用户普通终端可只读同一固定摘要入口并落盘；不重跑业务、不补模型次数。
  需要允许既有wrapper的真实授权环境，以及对未确认回传的明确处理范围。现未请求/执行重发。

### 2026-11-21 新授权带诊断Word业务执行：离线准备

- **明确授权与范围**：用户要求开始新一轮真实执行并启用已有分阶段诊断。冻结task
  CAL-WORD-PARAGRAPH-DIAG-001，单次120秒/清理10秒；仅原两文件Word段落导入与>=4项确定性测试，
  不重放CAL-WPF-001或CAL-WORD-PARAGRAPH-001，不扩大功能/权限/预算。
- **实际准备**：批准新worktree基于832836e，契约提交e83902c；8份项目拥有作者输入，经hash→build→
  validate现有入口READY，五门PASS/0错，manifest fa1efd946ceaa6ba767116430da8cec20b73938fa9cbc915b35d370a2312ebd8。
  初次离线调用顺序缺manifest被编译器拒绝，按入口既定顺序更正后通过；无发送或业务执行。
- **直接必要修正**：上轮无分阶段证据且读取需root，本轮复用既有launcher白名单与iap_diag_summary，
  在固定wrapper添加按登记task只读摘要模式。拒绝执行参数混用、未知task、穿越/符号链接/不可信归属，
  只读固定root-owned元数据，不开放shell/任意路径。7项汇总器+3项解析检查；仅本轮必要边界。
  初始测试fixture受umask影响成group-writable被正确拒绝；fixture固定可信权限后通过，未放宽生产判断。
- **当前实际状态**：非root --check CHECK_OK/DIAG_INPUTS_OK；root保护sink存在性UNKNOWN，必须root时
  拒绝已有场景。job CAL-WORD-PARAGRAPH-DIAG-001-AUTO已冻结并WAITING_PREPARATION，tick只等待。
  原始业务实现/模型/新控制发送/安装/登记/宿主验收均NOT_RUN；Windows NOT_RUN，正式main仍832836e。
- **下一步**：用户完成一次root认证，集中安装诊断读取必要字节、可信契约/登记及gate；后台按现有人类
  授权自动审查/派发/诊断汇报，实际成功才独立宿主验收。本次新授权前的旧失败仍保持，无新超时根因结论。

### 2026-11-21 scratch残留清单已自动接收并收口

- **实际证据**：用户执行只读find后，直接读取外部产物，无需搬运清单正文。SHA-256为
  `511019cbf32db45020b16b3043a99d6c0b77313a90218c7c00f5a92eab237f37`，51字节；
  仅scratch根目录与`hermes-snap-e4d68d5c0ce9.sh`（普通文件、0600、2975字节），没有子目录记录。
- **判读边界**：只读核对锁定Hermes源码tools/environments/base.py与local.py：该命名对应构造终端
  环境时init_session写入的shell环境快照，不是任务运行日志。文件存在不能证明模型响应或业务工具
  成功，也不能从此判定网络/模型/工具哪层超时。未读取快照内容、未source/执行、未改权限。
- **结论**：本次残留排查已完成，根因仍UNKNOWN，无新增可据以修复的代码问题。业务FAILED、
  系统实际BLOCKED/124且清理回传确认、宿主验收/Windows NOT_RUN均保持。未发送或调用模型，
  未重放消费身份，队列空。下一次真实执行须有新适用授权及已有阶段诊断，不能无证据重复尝试。

### 2026-11-21 用户要求继续：本次超时只读排查

- **实际推进**：读取安装态wrapper/launcher、Bridge执行与日志保留实现、任务登记、当前链和任务时段
  系统journal。队列无新待办；未模型调用、未发送、未重跑、未改权限或正式仓。
- **发现**：阶段sink未对该日历身份启用；执行函数虽取得原始stdout/stderr尾部，Bridge既有返回仅保留
  固定摘要且未持久化尾部。profile/session/broker日志位于已清理的运行目录，当前无法追溯。
  系统journal仅见启动，未查到能定位根因的记录；这不等于排除了网络、模型、沙箱或工具错误。
- **实际阻断**：唯一剩余可检查的scratch为aegl-ai/750，ACL无zhong读取权；诊断根目录root/700。
  无法读取不能写成空目录或sink不存在。超时根因仍UNKNOWN；业务FAILED、宿主/Windows NOT_RUN不变。
- **必要下一步**：用户认证一次固定路径`find -P`只读残留清单，输出原子写入项目外产物目录，
  由后台自动读取；不改ACL、不建诊断框架、不执行任何残留文件。没有新代码问题可据此修复。

### 2026-11-21 CAL-WORD-PARAGRAPH-001 授权恢复与真实业务执行（FAILED）

- **规则**：按用户明确修改，授权范围内对原因明确且安全可证的故障自动修复并走有界审计恢复；
  保留原失败、链值和预算，不盲目重发、不重放消费身份。全局AGENTS与后台提示已同步。
- **必要修复**：首次CDP配置失败经INITIAL_READ_RECOVERY恢复；首次读取bootstrap重启丢模块路径，
  改为状态修改前选择官方Hermes运行时并固定入口路径。23项针对性测试PASS，含已发送拒绝续接、
  链值/消费保护与续接不增加动作计数；隔离runpy入口也实际可读pending。
- **真实链路**：正式adapter只读确认精确请求不存在，追加BOOTSTRAP_READ_CONTINUATION；同一job、
  task、manifest和120秒预算续行。一次控制发送、ACCEPTED seq19、一次受控业务执行。
  结果BLOCKED／exit124／timed_out=true，phases KILL/TERM，cleanup CONFIRMED，回传CONFIRMED_SENT。
  CLI退出0不代表业务成功。Bridge现WAITING_FOR_GPT／seq20／pending=false。
- **业务结果**：FAILED。worktree HEAD仍59f9b807，status为空；两个要求新增的源码/测试文件均不存在。
  宿主验收NOT_RUN（必须先真实SUCCESS）；未声称零匹配通过。Windows实机NOT_RUN。
- **自动回报**：原队列已自动提交当前聊天；读取冻结plan和真实结果后ack确认。job HUMAN_REQUIRED，
  report `0c9b2030…`，result `22f1aeba…`，完整证据在外部agent-link/jobs/CAL-WORD-PARAGRAPH-001-AUTO。
- **收口**：SYS-11/12入口修复收口；新的业务超时根因UNKNOWN，scratch为aegl-ai/750不可读。
  自动派发/审查回写/失败回传实证通过，成功开发与独立验收闭环未通过。原任务身份和预算已消费，
  不重发、不恢复、不另建身份、不晋升。下一方向为现有权限/证据下查明超时；不扩建诊断设施。
  正式main仍832836e，未修改。源码仅批准Stack副本，未正式晋升/安装。

### 2026-11-21 CAL-WORD-PARAGRAPH-001 自动派发入口失败

- **授权与准备**：本轮用户已明确授权日历实际开发与自动接力；用户 root 命令成功，安装/登记/gate
  PASS，不再缺 root。原 120 秒执行预算与失败即停条件保持不变。
- **实际链路**：准备就绪后本地初报自动生成并排入当前聊天；当前聊天审查并写回 execute_contract。
  Bridge 首次读取前抛 AdapterError：`BU_CDP_URL must equal http://127.0.0.1:9333`；
  返回 READ_FAILED、包装 exit 1。它不是 Hermes 退出码：Hermes 未启动、控制请求未发送、身份未消费。
  失败已自动排入当前聊天并 ack；job HUMAN_REQUIRED。Bridge ERROR/seq19/pending=false。
- **业务与设备**：worktree git status 为空，正式 main 仍 832836e；未产生段落导入器或测试，
  业务/宿主验收 NOT_RUN，Windows NOT_RUN。原 CAL-WPF-001 的失败不变。
- **系统问题与修复**：新增 SYS-11，明确是本次接入缺少正式 adapter 环境。仅在入口补齐缺省的
  固定 EXPECTED_CDP；错误端点或 BU_CDP_WS 仍拒绝，检查提前在 Bridge 状态修改之前。
  16 项针对性测试通过；源码修复不冒充已安装或真实重试通过。
- **收口决定**：本轮失败停止，未重试、未 recover、未改 state、未另建身份。原因明确，值得只修
  接线后继续；但已有 recover-preconsume 仅支持 CONTRACT_REJECTED，不支持本次 READ_FAILED，
  不能直接套用。下一步由用户决定是否继续及允许的可信恢复范围，不新增诊断/部署框架。

### 2026-11-21 日历真实自动开发接力：段落导入准备

- **用户选择与预定验收**：继续日历项目，验证“受控开发 → 自动汇报至当前聊天 → 审查指令回系统”。
  本轮为 `CAL-WORD-PARAGRAPH-001` 小切片；导入 Word body-level 段落，至少 4 项真实宿主测试通过，
  来源字节不变、字段/顺序/缺日期错误正确，且实际源码差异仅导入器与测试。
- **已完成**：新批准 worktree `/var/tmp/RILI-WPF-V2/WORD-PARAGRAPH-001/project`；只写契约，未直接
  开发业务代码。HEAD `59f9b807…`，manifest `b451b36c…`；五门 READY/0 errors。
  初次编译因非 UI DESIGN 缺既有标题被拒绝，补齐后重新编译通过，未绕过门禁。
- **自动接力**：job `CAL-WORD-PARAGRAPH-001-AUTO` 已冻结在外部状态目录，WAITING_PREPARATION；
  新状态确保 root 登记前不调用模型、不发送、不消耗任务。登记与真实 gate 通过后才自动推进同一 job。
  120 秒执行预算与失败停止不变；已有本轮用户授权，不重复逐步申请。
- **必要改动与验证**：复用原 calendar prepare.sh，增加任务参数并查询实际 Git 元数据路径，避免复制
  每任务准备脚本；bash 语法及该任务 `--check` PASS。队列准备等待相关测试共 15 项 PASS。
  它们直接解决下一次 root 准备和自动续行步骤，不新增部署或诊断框架。
- **真实阻断**：新任务不在 root registry，trusted/registry 当前不可写，须用户输入密码完成一次 root
  安装/登记/gate。未调用 sudo；未新发 Chrome 控制块、未 round、未执行模型/业务/宿主验收。
- **三类结论**：离线准备 PASS；业务与真实系统执行 NOT_RUN；Windows NOT_RUN。旧任务
  CAL-WPF-001 的失败与 SYS-09 UNKNOWN 保留，不回填、不重放。
- **下一步**：用户执行已审查 root 命令；后台读取真实登记后自动报告、审查、单次派发与验收。
  如失败或一小时窗口耗尽立即停止，不重试、不延长、不另建身份；正式仓保持只读，不晋升。

### 2026-11-21 当前聊天自动接力、后台调度及业务派发接口

- **用户方向**：继续接通当前聊天直连、后台持续推进和业务动作自动派发；保留失败停手与单次业务授权。
- **实现**：新增持久 job 队列和固定动作；复用原 supervisor 锁、原子写入和原 Bridge；在 Bridge
  锁内增加可选 entry guard，先检查冻结范围、消费记录和真实 gate，再走单次 Chrome 控制协议与
  原受控执行。宿主验收仅支持已配置的 dotnet 测试外部副本、只读宿主沙箱及非零 TRX 计数。
- **实际验证**：14 项新增测试通过（错聊天／旧哈希／计划变更拒绝，消费身份拒绝，失败与中断
  不重试，发送不确定不重发，业务完成必须宿主验收，零匹配不通过，停止请求及真实沙箱写入边界等）。真实预检查
  CAL-WPF-001 因已消费被拒绝，未触发 gate、浏览器或 round，Bridge state/journal 字节未变。
- **当前聊天**：正式 `codex queue` 探针与两份自动汇报均实际到达本聊天；已完成审查、一次核对指令、
  本地回报及本聊天最终 COMPLETE，不用剪贴板。job `STACK-CURRENT-CHAT-AUTO-20261121`
  仅有读报告权限，task=null；两次回报、一次限定读取。独立核对 receipt、冻结 plan/hash、结果与
  Bridge seq 19 一致；初报的清理／回传标签经核对纠正，不把报告文字直接当事实。
- **后台**：通过应用原生工具创建并启用 heartbeat “Stack 当前聊天自动接力”（ID `stack`），
  每分钟检查队列，无变化安静。2026-11-21 08:49（Asia/Shanghai）首个系统 heartbeat 实际到达
  当前聊天并完成队列读取，待办为 0；后台唤醒／回调已实证，没有后台业务动作可派发。
  无新增问题；未发送、未调用模型或执行业务。电脑与应用须运行。
- **问题变化**：无新增业务运行故障；SYS-09 保留 UNKNOWN。当前聊天缺 control socket 的接入限制
  由正式 queue 接口解决，未绕用内部 IPC；既有只读自动往返保持收口。
- **三类结果与边界**：接口／门禁离线验证 PASS，当前聊天收报 PASS；新业务真实执行与业务宿主
  验收 NOT_RUN；原日历任务仍 FAILED/124/0 Word 测试，Windows NOT_RUN。没有新业务单次授权，
  不创建替代任务、不重跑旧任务，不将当前接入开发冒充受控业务结果。
- **源码与安装**：只在批准 Stack 副本变更；调度为本机用户应用配置，未晋升正式树、未 root 安装。
  当前聊天往返验证及首次后台唤醒已收口，后台保持授权范围内队列检查；不为文档指标再造任务。
  新的业务真实验证仍需具体且未消费的授权范围。

### 2026-11-21 本地 AI ⇄ Codex 自动汇报最小闭环

- **目标与预定验收**：用户授权建设自动报告与审查通道，接受独立 Codex 审查会话。
  本地 AI 自动提交现有失败报告，Codex 给出一次限定只读核对指令，本地 AI 自动接收并回报，
  Codex 最终收口；全过程无需用户搬运消息，不重跑 CAL-WPF-001。
- **实际结果**：官方 App Server stdio + Command Code JSON 接口完成四条消息、一次固定报告读取，
  最终 `COMPLETE`。通信标识 `STACK-REPORT-LINK-FORMAT-FIX-20261121`，
  审查会话 `01a1fb78-0ec7-7320-8253-8e21ee691917`。14 项边界测试通过；独立核对报告哈希、
  回报事实和四消息结构一致，Bridge 仍 seq 19，正式仓与日历 worktree HEAD/状态未变化。
- **实际问题**：默认 Codex control socket 不存在，按用户选择使用独立会话，未绕用内部 IPC；
  首次通信因本地 JSON 回报不合规被拒收（原通信记录保留），修正输出模板后验证通过，记 SYS-10。
  启动时另有一次哈希参数笔误，在创建状态或模型调用前被拒绝并更正；不是业务重跑。
- **源码／安装／验证**：新增 `supervisor/agent_link.py`、`agent_link_worker.mjs` 与对应测试，
  复用既有 supervisor 锁与原子状态写入；源码仅在批准 Stack 开发副本。未正式晋升、未可信安装。
  已完成真实只读模型通信；传输队列处理、严格类型与持久化防重入另有针对性离线测试。
- **三类结论**：通信最小闭环 PASS；日历业务仍 FAILED/BLOCKED、exit 124、Word 测试 0；
  原业务受控链路没有新增执行；Windows 实机 NOT_RUN；SYS-09 根因仍 UNKNOWN。
- **未覆盖**：自动派发业务动作、当前桌面聊天直连、原交互会话接管、常驻服务、任意项目接入。
  当前只允许 `inspect_evidence`；本地端禁用工具，审查端使用只读沙箱，不执行回复中的 shell 文本。
- **收口与下一方向**：本次通信验收收口；后续复用通道承接明确授权的既有可信动作，
  沿用原契约、沙箱、预算与失败停手条件。没有重跑旧任务、修改正式树或新增诊断框架。

### 2026-11-21 CAL-WPF-001 首次受控执行（FAILED / BLOCKED）

- **业务目标与验收**：Word `.docx` Infrastructure importer + 确定性测试；宿主验收要求
  `WordImportTests` 实际执行数 > 0 且全通过，源 `.docx` 哈希不变，变更范围受限。
- **实际结果**：控制请求单次 `CONFIRMED_SENT`；新 assistant 唯一控制块通过本地协议校验；
  一次 round 返回 `outcome=BLOCKED`、任务 `exit_code=124`、`timed_out=true`、
  timeout phases `KILL/TERM`；清理 `CONFIRMED`；结果回传 `CONFIRMED_SENT`；
  result `63355a6f…`；链推进到 seq 19。
- **业务变更与验收**：worktree `git status` 为空，无 Word 文件；宿主筛选
  `WordImportTests` 实际 **0 个测试匹配**，不通过。对照 `ExcelImportExportTests`
  4 项通过，说明测试基础设施正常。
- **系统问题变化**：SYS-07 因用户完成 root 准备而收口；新增 SYS-09（超时且无变更，
  无任务级诊断，根因 UNKNOWN）。SYS-01—06、08 状态不变；未重跑 005，未创建 006。
- **修复生效位置**：无新修复；本轮没有修改系统源码。root 准备脚本与契约哈希保持
  `9a3ae34a…` / `639ed1fe…`（该脚本为上一轮修复后的版本）。
- **未覆盖或无法证明**：超时根因、Hermes 内部工具调用、scratch 内容（无权限）、
  Windows 实机。全部 UNKNOWN/NOT_RUN。
- **收口决定**：失败立即停止；不重发、不重试、不 recover、不延长预算、不另建任务；
  正式仓保持只读，未晋升。
- **下一步**：由用户决定是否调查 UNKNOWN、是否使用既有诊断白名单，或在有依据后另开任务。

```text
日期／任务／业务目标：2026-11-21／CAL-WPF-001／Word .docx 导入受控执行
预先约定的独立验收：WordImportTests 数 >0 全通过；源 docx 哈希不变；范围受限
实际结果：控制 CONFIRMED_SENT；round BLOCKED/exit 124；cleanup CONFIRMED；回传 CONFIRMED_SENT
已证明的范围／证据摘要：worktree 无变更；WordImportTests 0 匹配；对照 4 项通过；seq 19
本轮系统问题：SYS-07 收口；SYS-09 新增 UNKNOWN
修复生效位置：无新修复；未修改系统源码
未覆盖或无法证明的部分：超时根因、工具调用、scratch、Windows 实机
收口决定：失败停止，不重试/不 recover/不新建
下一步：用户决定是否调查或另开任务
```

### 2026-11-21 CAL-WPF-001 接入纠正与离线准备

- **业务目标与验收**：为 Word `.docx` 导入建立受控任务；契约 READY；宿主在 round 后运行
  `dotnet test ... --filter WordImportTests` 并校验源 `.docx` SHA-256 不变。
- **实际结果**：CAL-001 由 `3b05f6f` 正常快进到 `832836e`，随后在 worktree 提交文档与
  8 个作者输入（HEAD `fdcb91a`）；契约五门 PASS、READY、errors=0，
  manifest `639ed1fec89a9af7f67b0bb080c169aeb91ab3adb2b0d8c394f99c21fb83d105`。
  **没有发送任务控制块，没有 round，没有 Hermes 退出码，没有宿主验收。**
- **Chrome 咨询**：普通技术咨询实际 `CONFIRMED_SENT`，新响应 SHA-256
  `b9632fe2…`、2586 字符；证据在业务产物目录，不是控制块、不是执行授权。
- **系统问题变化**：新增 SYS-07（外部权限阻断）和 SYS-08（前阶段流程偏离已记录）；
  没有新增系统代码缺陷。SYS-01—06 状态不变；未重跑 005，未创建 006。
- **修复生效位置**：Stack 开发副本已有精确 binding；AEGL 开发副本新增
  `recovery/calendar_wpf_001/prepare.sh`（仅源码，未 root 安装、未执行 root 阶段）；脚本对正式仓的 root Git 查询使用命令级 `-c safe.directory=$PROJECT` 并保留失败输出。
- **未覆盖或无法证明**：trusted install、register、真实 gate、launcher 挂载、Hermes
  执行、Windows 实机。全部 UNKNOWN/NOT_RUN。
- **收口决定**：在唯一的 root 外部阻断处停止；离线契约与只读检查已完成，
  交付一条可核验的 root 准备命令及成功标记。
- **下一步**：用户执行该 root 命令；成功后重新读取 Bridge seq/nonce/in_reply_to，
  单次发送唯一控制块并执行一次 round。

```text
日期／任务／业务目标：2026-11-21／CAL-WPF-001／Word .docx 导入受控任务准备
预先约定的独立验收：契约 READY；round 后宿主 dotnet test WordImportTests；源 docx 哈希不变
实际结果：无发送／无 round；契约 READY；咨询 CONFIRMED_SENT；root 准备 BLOCKED
已证明的范围／证据摘要：manifest 639ed1fe…；五门 PASS；worktree Git 归属 OK；--check CHECK_OK
本轮系统问题：SYS-07 外部权限阻断；SYS-08 流程偏离已记录；无新增代码缺陷
修复生效位置：Stack binding 已提交；AEGL prepare.sh 源码已提交；未 root 安装
未覆盖或无法证明的部分：trusted install、register、gate、launcher、Hermes、Windows 实机
收口决定：停在 root 外部阻断，不发送控制块
下一步：用户运行 root 准备命令；成功后发送唯一控制块并 round 一次
```

### 2026-11-21 日历接入只读审查与方向纠正

- 已只读核对业务接入文档、Git 记录、Bridge state/journal。文档明确承认此前代码由普通会话直接完成，契约作者输入、可信登记和受控执行尚未完成；binding 和 Git 归属检查仅证明接入准备。
- 审查快照：Bridge `WAITING_FOR_GPT`、expected_sequence=18、last_task_id=SYSTEM-E2E-005、无 pending；journal 44 条，无 OfflineTaskCalendar_WPF／RILI-WPF／CAL-001 匹配。此快照不是后续运行状态。
- 审查当时的 Chrome 自动咨询未取得本项目请求／响应关联证据，状态为未验证；随后本轮实际发送了一次普通技术咨询并取得 `CONFIRMED_SENT` 与新响应（见业务仓 `docs/CONSULTATION-LOG.md`），但它不是控制块、不是执行授权。
- 正式业务仓当时 HEAD=832836e，CAL-001 worktree HEAD=3b05f6f；未取得可信晋升记录，不能据此证明全程隔离开发，也不据此断言每次编辑发生的位置。
- 对下方旧报告“无新增系统缺陷／继续独立推进业务”的补充纠正：尚未运行的受控链路不能据此判定无缺陷；新项目可信接入是实际阻断，转为普通会话开发是流程偏离。权限边界本身不等于代码 bug；通用接入能力缺口仍需核实。
- 该审查本身只读；随后本轮完成了离线契约、只读 `--check` 与 root 准备脚本，并实际发送了一次普通咨询；仍未执行模型 round、sudo 安装、任务登记或业务代码修改，未重跑旧任务。保留业务成果，以一个真实日历功能接通现有链路；随后检验是否可复用于其他项目，不能以本项目专用接线替代总目标。

### 2026-11-21 OfflineTaskCalendar_WPF 阶段 0–2

- **业务目标与验收**：C#/WPF/.NET 10 离线任务日历；阶段 0–2 需完成环境核对、
  旧版只读审计、解耦工程、SQLite、类型/主题/颜色优先级与首个竖切。
- **实际结果**：`dotnet build` 成功；Core 47 项、Infrastructure 36 项测试通过
  （共 83）；WPF 仅 Windows 目标交叉编译成功。竖切“授课主题→保存→日历标签→重启读取”
  有自动化证据；Excel/CSV 导入导出、列映射预览、草稿/批次撤销、旧库只读 dry-run 迁移在 Ubuntu 通过；
  `win-x64` self-contained 交叉发布包已生成但从未在 Windows 启动。
  Windows 窗口/托盘/动画/发布为 NOT_RUN。
- **系统问题变化**：无新增系统缺陷。SYS-01—06 状态不变；未重跑 005，未创建 006。
- **已完成的接入准备**：在 Stack 授权开发副本增加精确 binding
  `OfflineTaskCalendar_WPF`（限定项目根与 `/var/tmp/RILI-WPF-V2/` worktree，
  `require_git_ownership=true`），新增 4 项测试，bridge 项目测试 11 项通过；
  隔离 worktree `/var/tmp/RILI-WPF-V2/CAL-001/project` 的真实 Git 归属验证 OK。
- **环境阻断（非系统缺陷）**：可信契约目录位于 root 拥有的
  `/var/lib/aegl-model/trusted/`；`aegl-model-task register` 仅 root；
  当前非交互 sudo 不可用，sudoers 只放行受控 wrapper。因此契约安装、任务登记、
  安装版 bridge 更新与受控执行均 BLOCKED/NOT_RUN，没有提权或绕过门禁。
- **业务缺陷修复（不属于系统问题）**：迁移事务嵌套、撤销完成写空 `updated_at`、
  `shown` 提醒重复返回、提醒唯一键导致重复插入、周重复顺序、相对周日期、
  SQLitePCLRaw 高危依赖、NPOI 加密包高危依赖、Excel 时间列未映射、
  全天任务重复键、Excel 日期序列、旧库默认时间误判为全天；均有测试或构建证据。
- **收口决定**：业务阶段 0–2 完成；系统接入在权限边界处停止，继续可独立推进的
  业务开发。Windows 与受控执行恢复需 root 或 Windows 资源。

```text
日期／任务／业务目标：2026-11-21／OfflineTaskCalendar_WPF 阶段0-2／建立可离线 WPF 工程与首个竖切
预先约定的独立验收：构建成功；核心/持久化测试通过；授课主题竖切可重启读取；WPF 仅交叉编译
实际结果：无受控发送（无登记任务）；本地构建/测试 PASS；Windows 实机 NOT_RUN
已证明的范围／证据摘要：Core 47 + Infra 36 + bridge 11；worktree Git 归属 OK
本轮系统问题：无新增；SYS-01—06 不变；未重开 005
修复生效位置：业务仓本地提交；Stack 开发副本 binding 提交；均未做 root 安装
未覆盖或无法证明的部分：Windows 行为、win-x64 发布、受控执行、契约信任安装
收口决定：阶段完成；系统接入在无 root 处停止
下一步：继续阶段 3–6 业务实现；Windows 或 root 可用时再恢复实机与受控执行
```

### 2026-11-21 整理：SYSTEM-E2E-005

- **目标与验收**：完成一次受控契约编译任务并回传结果；独立检查实际产物达到 8/1/1/READY/0，输入和 fixture 未变。
- **实际结果**：单次请求发送确认；任务 SUCCESS / 0；清理报告 PASS；结果回传确认；独立 `ACCEPT=OK`。精确工具调用次数 UNKNOWN，不能从产物时间戳推断。
- **系统问题变化**：SYS-01—03 对应修复已用于本轮，保持收口；SYS-04 本次经授权恢复；SYS-05—06 保留证据限制。没有据此新增源码修复或验证框架。
- **决定**：任务与独立业务验收通过，收口。不重跑 005，不自动创建 006。
- **下一步**：等待用户选择实际业务目标；只把真正阻止该目标的问题列为前置条件。
