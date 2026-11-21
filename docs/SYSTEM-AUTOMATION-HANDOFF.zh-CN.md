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

**Cursor 接手：绝对路径提示已加强，新任务已冻结等待 root**：用户分享对话后由 Cursor
会话接手未完成的 SYS-16。仅文字说明路径基准仍不足以让模型跳过寻址；生成器现将
`source_root`/`read_first`/`allowed`/`forbidden` 写成绝对路径，包成员统一写为
`$HERMES_CONTRACT_PACKAGE/...`，并禁止 `find`/`ls` 定位契约。相关 CLI/build 共 13 项通过；
Stack 提交 `1677f82`。新业务身份 `CAL-WORD-PARAGRAPH-ABS-001` / job
`CAL-WORD-PARAGRAPH-ABS-001-AUTO` 已 submit 为 WAITING_PREPARATION；worktree
`/var/tmp/RILI-WPF-V2/WORD-PARAGRAPH-ABS-001/project` HEAD
`591e9ac132bbf654f1605aa95793cf2b1f72c372`，manifest
`96d144ecbc936b234fd13511c98e98f2dfbca668fcfb57fa4dc9e00515955f9a`，五门 READY；plan_sha256
`6774ea931bc04532322891ac7abcc8aa438dc6fdceadf49b76030a67d01839d9`；`--check` 与
DIAG_INPUTS_OK 已通过。旧四个失败身份不重放。业务执行/宿主验收/Windows 仍 NOT_RUN，
待用户普通终端一次 root prepare --diagnostics 后接 host-run；本会话经 agent_link decide/ack
审查，不自动延长或另建替代任务。

**guard请求已核对，本轮查因不再等待用户读取**：新提取exit0/stderr空，输出SHA
`794007fa623220f3c4dd7f3ade2551bf54b9cb2c5a1876624d00a8dcf225e65f`；原capture SHA
`cf770cb02da82e326a829cada5a934880c072b5284fc7ea2d308f7c4c527a27a`，11条、无坏行，全部真实请求
相关性及记录标记通过，guard rc均0。模型未显式传workdir；6条请求出现find词、7条出现ls词，
多次出现相对契约文件引用，无一命令hash逐字匹配两个冻结CLI检查。词提示不是完整shell语义；请求
中有cd，不能仅凭相对文件名认定每次读取都用了启动cwd。guard正常ALLOW不输出JSON，摘要中
guard_decision=UNKNOWN不表示guard阻断，也不为此修改guard协议。

已确认的系统缺口是提示缺少契约/源码路径基准，实际请求又持续出现契约查找行为；这支持启动寻址
消耗预算的判断，但现存脱敏记录没有4个原始tool_error正文或每次工具内部cwd，不能声称唯一超时
根因已完全证明。修复在原提示生成器：明确包目录HERMES_CONTRACT_PACKAGE、源码source_root及
CLI登记cwd，并给出一次printf取包目录、批量必要读取、禁止重复寻址的明确步骤。新增独立cwd下
执行该只读定位命令的回归通过；相关CLI9项、build3项共12项通过。未重跑业务/改旧冻结包，当前
修复为源码及离线验证完成，尚无修复后真实开发成功证据。业务仍FAILED、宿主验收/Windows NOT_RUN。
本轮提取收口，不追加日志字段或诊断设施。下一真实业务执行需新的适用未消费授权；不自动创建任务。

**工具结果已读取；路径提示缺口已修复源码，因果核对仍待既有请求记录**：用户认证后的
phase-summary-tools提取exit0、stderr空，SHA `1f82794897256d052fb6739082c85bd794bcc43676fa7432c3185672590a69f6`。
20个post中4个ERROR（terminal三次exit1/2/1，read_file一次）、16个OK；无write_file/patch事件。
工具返回快，不能据此认定工具卡死；terminal是否尝试写入仍须核对实际请求，不能只凭工具名判断。
静态核对确认：sandbox启动cwd为登记worktree，而提示中包文件仅给相对名、read_first给相对source_root
的project/src路径；这些路径若直接相对cwd读取全部不存在。提示生成器已明确包目录来自
HERMES_CONTRACT_PACKAGE、源码路径相对project-context.source_root、CLI保持登记cwd；11项既有相关
检查通过。此为确定的提示路径基准缺口修复，尚不能证明它就是本轮4次错误及总超时的唯一原因。
未重新生成/改写已消费任务的契约、manifest、state或预算，业务仍FAILED，宿主/Windows NOT_RUN。

为核对真实调用，复用AEGL现有read_004_guard_args.py的固定字段提取，新增精确已登记--task模式；
只输出guard判定、命令hash、固定参数及声明文件引用基准/固定词提示，不输出完整命令、正文或凭据。
3项针对性检查通过，源码SHA `83b5744de11095d1b4b30e6154b0ea6f3cad6ae39f1037d9fe5ff82ad6ca4cbd`。
需用户普通终端一次认证读取同一旧任务的guard-capture，落盘guard-request-summary.json并官方queue
自动回执；无安装、模型或业务重跑。未获得该记录前不把4个tool_error自动判定为路径错误。

**用户要求继续查根因，已修正现有摘要的工具结果遗漏，尚待读取真实结果**：AEGL现有
`recovery/iap_diag_summary.py`补充严格整行解析broker已采集的tool/status/error/duration/exit固定字段，
不输出命令、结果正文或原始arg；10项相关检查通过。源码SHA
`26f1cbbb937c582a793abec01540cd3a7222c0d89b99bc2ac2707780fc5d21bf`。
prepare同步固定新摘要SHA，仅接受已安装旧版或新版，未执行安装或重新登记。
当前桌面实测NoNewPrivs=1，root诊断目录700，不能自行提权读取；尚未得到本轮工具状态，业务超时
根因仍UNKNOWN。交付用户普通终端只读提取：root进程单次读取并验证该源码字节哈希，在内存中执行
同一任务绑定摘要器，结果写回job外部state目录`phase-summary-tools.txt`；不安装、不运行模型、不改链值。
用户认证后读取新文件继续定位。未重跑/新增任务；此前旧摘要与失败记录保持原样。

**HOST-001 已实际执行并超时，覆盖下方 READY 等待快照**：用户普通终端重启同一 host-run 后，
当前聊天已审核的 execute_contract 被宿主取走；seq21 实际 ACCEPTED，单次120秒返回
BLOCKED/exit124，timed_out=true，清理CONFIRMED，结果CONFIRMED_SENT，Bridge现
WAITING_FOR_GPT/seq22/pending=false。任务身份及预算已消费，不重放、延长或自动创建替代任务。
失败报告 `c7b57f1439d6187ece2d42a738d26f57bec2adafaef487efc4652383152e4877` 已由当前聊天 ack；
job HUMAN_REQUIRED。worktree仍f18b30f、status为空，两个要求源码/测试文件均不存在；业务FAILED，
宿主业务验收NOT_RUN，Windows NOT_RUN，正式main仍832836e未修改。

宿主一次读取既有阶段摘要成功（exit0，SHA `58360e87578a1523a4fc50bd3b4ba5453e8a2ce71716bc53ee669ea6f936716d`）。
308条元数据证明sandbox准备/启动请求、14次完整模型响应、20对工具pre/post事件、11次guard返回0；
第15次上游请求收到HTTP200响应头后未记录body完成即到期。由此确认本轮已越过旧NNP执行入口阻断，
并非没有接通模型。不能把guard返回0或工具post事件当业务命令成功；现安装summary不输出arg内
工具status/error/exit/duration，scratch当前不可读，故“为何反复调用而无代码”的根因仍UNKNOWN。
不据最后一个未完成响应推定网络是根因，也不回填旧超时原因。不为补证重跑业务或新建诊断框架。
当前已无可派发授权动作；下一方向仅限既有证据与权限内查明工具执行失败/无产物原因。

**本轮root已成功，初报CLI定位故障已修复，当前READY等待宿主恢复**：用户已执行组合命令，root
REGISTER/GATE/PREP_COMPLETE成功，安装三SHA匹配。普通宿主初报模型已生成正确REPORT，但初报入队
因PATH找不到`codex`抛FileNotFoundError，未启动通知进程，旧代码误标SEND_UNCERTAIN并结束host-run。
原报告SHA `6918a73e378e49f7bd6af4b516af373fa9d9d3c90a8b1c2c155891656a389571`，无actions/results，
业务身份未消费，Bridge仍WAITING_FOR_GPT/seq21/pending=false，Hermes和120秒业务预算未动。

- 修复在原入口：CLI解析优先显式`--codex-bin`、CODEX_APP_RUNTIME_CLI_PATH、PATH，再兼容本机已安装
  桌面CLI `/usr/lib/chatgpt/resources/codex`；host-run在调用报告模型前检查Codex/Command Code可执行文件。
  队列启动前失败单独NOT_SENT且保留已生成报告；真正已启动的发送不确定仍拒绝自动重试。
- 新增受限recover-notification-start，仅接受初报、空动作/结果、固定报告hash/源hash、准确ENOENT或
  NOT_SENT事实、未消费且gate通过、原窗口剩余足够、未用恢复额度。保留完整失败快照，只用已保存REPORT
  重新通知，不重调模型、不改契约/计划/链值。宿主未来遇此已知故障可在原窗口等恢复，不提前退出。
  36项队列/宿主针对性检查通过；clean PATH/无CODEX环境的官方queue --help实际通过。
- 当前恢复已实际执行：在普通终端类似环境（去CODEX环境、保留NNP限制）用官方绝对CLI，将同一REPORT
  QUEUED成功，new_model_call=false；notification_recovery_history保留ENOENT。当前聊天已核对原授权、
  report/plan及真实安装/manifest/root gate，decide execute_contract写为READY，actions_done仍空。
- 用户只需普通终端重启同一host-run（可显式--codex-bin /usr/lib/chatgpt/resources/codex），不用重跑root
  prepare、不创建新任务、不重新生成报告。原宿主已退出，桌面不能代为绕过NNP启动它。planSHA、manifest、
  单次120秒/清理10秒和原deadline全部不变。后续仍由宿主执行/读取诊断/验收，桌面只审查决定。
当前业务/宿主业务验收/Windows均NOT_RUN；下方“等待root认证”等已为历史，不能再次要求用户准备。

**新的真实开发验证已获授权并冻结，等待用户一次普通终端启动**：用户在宿主核验通过后明确要求
“那开始：接下来需要验证修复后的真实开发流程”。本轮task `CAL-WORD-PARAGRAPH-HOST-001`，job
`CAL-WORD-PARAGRAPH-HOST-001-AUTO`；只开发原Word段落导入器和>=4项确定性测试，单次Hermes120秒、
清理10秒，无表格/UI/新依赖/数据库/晋升；旧三个失败身份不重放。这是用户新授权，不是系统自动换身份。

- 新worktree `/var/tmp/RILI-WPF-V2/WORD-PARAGRAPH-HOST-001/project`，基于正式832836e，只有项目契约
  提交`f18b30f35513dcce5b7fdfe9111a1d70c200e196`。manifest
  `f93a9583154d5cd6e6be9f73a90aeb809ecaff123b2ee85b9cd13c3a463158f3`，五门PASS/READY/0错。
- plan SHA `825c0bec523a25db19a0e95e3ec495b38915dc5c9d36044d637ade65eef24a3f`；证据文件任务根
  preparation-summary.md，SHA `80960dcd66546fc63c00aa93ae38c102fcd1ddca38b56ef2f4262de768ab23c6`。
  已submit为WAITING_PREPARATION，actions_done空，无模型/发送；总窗口沿用冻结的一小时，不延长。
- 必要准备修正：原脚本仅接受升级前哈希，会拒绝已成功安装的诊断组件。本轮复用当前root-owned
  wrapper/summary，不重复安装；launcher除受严格语法/基线/登记检查的任务配置行外，全部代码字节
  仍固定SHA `0c8aafde79be9b2564ef771d97ed78982aa5887790da50d84147b2d2d19174ec`。
  只追加本task诊断配置，拒绝未知任务、重复/命令语法、其他代码改动；5项针对性检查与--check实际通过。
- root完成后预期launcher SHA `71b8d9e149a37f08b6d7c34eaeca61b87ed81c1293f668afd29c89c15899f73d`，
  wrapper e8b90a5a995795555ef077482f0a80cc14a6249815e1c182decca4444e398725，summary
  5a3f3923fa186cc8770e5b6ef806627ca53895ab183051dd41e9c8ad520b84eb。sink存在性仍由root检查，当前UNKNOWN。
- 用户将在同一普通终端命令里先root prepare --diagnostics，成功后普通用户host-run（不带check-only），
  绑定上述job/thread/plan。桌面不tick，不sudo、不在外部偷偷拉起进程；只pending/decide/ack。用户已给
  单次业务授权，不重复申请；尚缺的是root认证和用户显式启动宿主。宿主等待当前聊天决定后取指执行。
- 实际退出后宿主在job外部state目录读取一次phase-summary.*；真实SUCCESS/0、cleanup和回传确认
  后才下发host_acceptance，WordParagraphImportTests实际>=4且全通过、核对真实差异/断言/源docx哈希
  才COMPLETE。失败保留真实诊断并停本轮，不扩预算/模型次数/替代身份。安全可证的发送前失败仍只走
  已审查有界恢复；宿主可在原deadline内等修复，已消费失败不恢复。Windows保持NOT_RUN。
当前正式main仍832836e未变，root准备/业务执行/宿主业务验收均NOT_RUN；下方宿主旧任务核验已收口。

**宿主只读核验已通过**：用户普通终端生成host-context-check.json，已实际读取并核对：
host_context=READY、execution_attempted=false、job_id=CAL-WORD-PARAGRAPH-DIAG-001-AUTO、
status=HUMAN_REQUIRED；文件SHA `8ccb13e2be7bd825bdde63f46b37bd0b155a2a4f0c6eefd66ffdcf51c05acf33`。
HUMAN_REQUIRED是旧失败job原有状态，不是宿主核验失败；没有调用模型、重跑业务或改变任务状态。
该检查只证明宿主入口的权限前提和冻结绑定通过，不证明真实sudo执行/模型开发/业务测试已通过。
回传已实证修复、宿主源码及环境核验通过；完整自动开发仍未完成真实业务验收。至此不再追加只读
环境检查。下一业务验证必须在正常宿主进程按新适用授权与未消费身份执行，再完成独立测试；不能
把旧任务重新标为READY。下方“宿主核验待执行”等为历史快照。

**用户要求查根因后，已完成的修复（覆盖下方旧停止快照）**：

1. **回传根因与真实修复**：只读现场显示完整canonical结果616字符仍在composer，用户turn中没有
   result_sha；输入框有焦点，同form唯一可用“发送”按钮存在。原Enter提交方式未完成提交。
   正式adapter改为同form唯一可见/启用submit按钮的物理单击，保留完整草稿校验、exact用户turn确认，
   无按钮不提交、异常不重试。用户随后明确授权仅补发此失败结果一次，经原HUMAN-ONLY resolver
   记录HUMAN_RESEND_AUTHORIZED后真实CONFIRMED_SENT/HUMAN_RESEND_CONFIRMED，resend_count=1。
   result仍`33b66caf…`／FAILED/exit1，未执行Hermes/重跑任务。Bridge现WAITING_FOR_GPT／seq21／
   pending=false。SYS-14回传阻断收口；旧SEND_UNCERTAIN报告e940…保留原样，不能回填为业务成功。
   证据：项目外send-resolution.json；原journal含补发授权、确认与RESULT。
2. **执行归属根因与修复源码**：进程链在桌面应用子进程层开始NoNewPrivs=1（其主进程为0），之后
   Codex→bash→python均继承1。当前代码把需要sudo的宿主执行放在此受限子进程内，是执行归属错误；
   不能在该进程清除标志。新增同一agent_link_jobs.py的有界`host-run`入口，由用户显式从普通终端启动，
   只绑定一个job_id/thread_id/plan_sha256、沿用原deadline/step/worker锁/受控wrapper/沙箱，不建新服务。
   当前聊天只pending/decide/ack；桌面tick遇执行动作且NNP阻断时保持READY且不改state/消费身份，
   宿主进程自动取已审核决定执行并回报。宿主内一次读取既有phase-summary，原始正文/arg不输出。
   安全的发送前已知错误可在既有窗口等待审计恢复，消费失败/不确定发送等仍退出，不补模型次数。
3. **实际验证与限制**：提交按钮4项、现有发送/精确确认/resolver相关26项、队列/宿主31项，共61项通过。
   现有normal-path测试stub缺task_id关键字参数已按已生效接口修正，未放宽断言。桌面真实host-run
   --check-only拒绝E_LAUNCH_NO_NEW_PRIVS，job字节不变。普通终端正向host-context核验现已READY；
   该核验绑定当前已失败job，仅只读、不调模型/不重跑。当前三个业务身份均仍消费失败，业务源码无实现，
   宿主业务验收/Windows NOT_RUN。不得把源码/上下文检查当真实业务成功，也不自动新建下一任务。

普通终端只读核验（不加sudo）：
`PYTHONDONTWRITEBYTECODE=1 python3 /var/tmp/IAP-CONTROL-DEV/stack/orchestration/hermes/supervisor/agent_link_jobs.py host-run --job-id CAL-WORD-PARAGRAPH-DIAG-001-AUTO --thread-id 01a1fb52-6dac-7f61-b200-1f8169e7a605 --plan-sha256 588351f7a8cb2a759af90e0e0298cc218d2368407a71c20f45d37e7b5a0b5ee3 --check-only`
预期host_context=READY、execution_attempted=false、status=HUMAN_REQUIRED。新业务须另有适用授权及
未消费身份；获授权时由用户启动同一宿主入口，桌面不得自行通过外部进程逃逸其权限限制。

**普通终端诊断已实际读取并收口**：用户执行同一固定只读summary后，后台文件已到达，退出码2；
stderr为`DIAG_SUMMARY_FAILED reason=FileNotFoundError`，stdout为空。本次不是成功读取到空事件集，
而是汇总器未找到所需诊断路径/文件。exit文件SHA
`53c234e5e8472b6ac51c1ae1cab3fe06fad053beb8ebfd8977b010655bfdd3c3`，stderr SHA
`4920df928214f8bc8e6170f7d2c3d9c903b713f14e21a63323058a23b5d58fd0`；已核对一次，不再等待或重读通知。
未获得sandbox_prep_begin或模型/工具阶段证据，不确认Hermes启动，不把当前权限故障回写为旧超时根因。
本次诊断排查收口，无需继续要求用户运行诊断命令。真正下一步是具备允许既有root wrapper的授权
执行环境，以及明确处理SEND_UNCERTAIN/pending的范围；当前进程不能清NNP或换进程绕过。三个已消费
业务身份都保持停止，不再创建任务试错。业务FAILED、宿主/Windows NOT_RUN，未重发/resolve，原失败保留。

**本轮最新失败与实际权限阻断（覆盖下方准备状态）**：用户已成功root准备，三项安装SHA/归属/模式、
精确诊断白名单均实际匹配。初报自动生成后第一次派发在发送前因9333未监听READ_FAILED，未消费。
按用户已有恢复授权，确认专用profile无进程后一次启动Chrome恢复原会话、一次恢复Harness；固定标签
恰好1个、composer=true/login=false/streaming=false，精确控制请求不存在。受审查入口扩展仅允许此
确切Connection refused，且只要同序号有任何SEND_ATTEMPT便拒绝；25项针对性检查通过，保留原失败
f4046836…并ack，经INITIAL_READ_RECOVERY沿用原seq20、任务、manifest、120秒预算继续。

随后控制请求实际发送、ACCEPTED seq20；受控入口返回FAILED/exit1、timed_out=false，cleanup UNKNOWN。
结果回传SEND_UNCERTAIN，result_sha `33b66cafddce038ccbb251873c87f5ddb242ee4ff29e9f52d4c950b242ee0042`。
只读精确确认canonical结果仍不在用户消息中，未重发/未resolve/未直接改状态。Bridge ERROR/seq20/
pending=true，身份已消费；job HUMAN_REQUIRED，失败report e940cb31646204be77d2ba71baa8101f28359aa9826060d4a448477eaac58b2e已ack。
worktree无改动，两个要求文件均不存在；业务FAILED，宿主验收/Windows NOT_RUN。是否实际进入Hermes
业务进程未得到独立证据，不凭Bridge EXECUTING标签认定模型已运行。

**新确认阻断**：当前Codex工具执行进程及父shell `/proc/status` NoNewPrivs=1。按约定只调用一次固定
诊断summary入口，sudo立即拒绝提权（exit1），汇总器未运行。不能放宽此标志、换外部进程绕过或声称
阶段诊断已取回；原业务stderr未持久化，不能把本次诊断错误回填为当时读到的业务日志。该事实与
业务入口快速exit1相符；至少已确定当前通道无法进入必须的root wrapper，原始阶段仍缺证据。
新增发送前权限检查：生产run_round在状态/浏览器/消费之前拒绝NoNewPrivs或UNKNOWN，不改权限；
3项针对性检查通过，防止继续消耗新身份。需要真正允许既有wrapper的授权执行环境，不能由本进程
清除NoNewPrivs。当前任务不自动重跑，未创建新身份，未重发不确定结果。

证据在 `/home/zhong/EXE/RILI/artifacts/controlled/CAL-WORD-PARAGRAPH-DIAG-001/`：
controlled-result.json、phase-summary-attempt.json（提权失败、空摘要，不是成功）、
phase-summary.stderr.txt、execution-context.json、pending-confirmation.json。
下一只读步骤可由用户普通终端调用同一已安装、白名单允许的diagnostic-summary并把stdout/stderr/exit
直接落到phase-summary-terminal.*；这不运行模型，不重复业务身份。后台只在新文件到达后核对一次。
没有新的执行环境与适用授权前，不再tick当前终止job。下方“尚缺root”等均为历史快照。

**新一轮已有明确用户授权，正在等待root准备**：用户随后明确要求“那开始：下一轮真实执行需启用
现有分阶段诊断，并明确授权新的执行范围和预算；已消费任务保持不重放”。本轮据此冻结
`CAL-WORD-PARAGRAPH-DIAG-001`／job `CAL-WORD-PARAGRAPH-DIAG-001-AUTO`，一次120秒
Hermes执行、原10秒清理宽限，仅Word段落导入器和>=4项对应确定性测试；无表格/UI/依赖/数据库/晋升。
这次是用户新授权的带观测业务执行，不是系统自动替换失败身份。两个旧任务仍FAILED/已消费，不改记录。

- worktree `/var/tmp/RILI-WPF-V2/WORD-PARAGRAPH-DIAG-001/project`，基于正式832836e，仅作者契约
  提交`e83902c3048fe60a312cfc84a27f8b3850e4533d`；无业务实现。正式main仍832836e未修改。
- manifest `fa1efd946ceaa6ba767116430da8cec20b73938fa9cbc915b35d370a2312ebd8`，五门PASS/READY/0错。
  冻结证据在任务根preparation-summary.md，SHA `317c498ad5aa2a1f8cc84e7618d521accb437ccb6823d4f470c47cc37838915c`。
- 复用calendar_wpf_001/prepare.sh的`--diagnostics`：精确核对现安装前驱与源码哈希，仅把本task加入
  既有launcher诊断白名单；安装现有汇总器的登记任务读取模式及固定wrapper `--diagnostic-summary`。
  诊断根目录仍root/700，不改ACL、不暴露任意路径、原始arg/正文/凭据。新增7项汇总器边界检查与
  3项wrapper解析检查；不是重开原传输/隔离套件。非root --check实际通过，sink存在性需root检查，UNKNOWN。
- 预期wrapper SHA `e8b90a5a995795555ef077482f0a80cc14a6249815e1c182decca4444e398725`，summary SHA
  `5a3f3923fa186cc8770e5b6ef806627ca53895ab183051dd41e9c8ad520b84eb`，launcher仅白名单变更后SHA
  `7f3d74c2e10b8e94101693cd126a35240694559bc54f990915312d2f2576a0a2`。
- job已WAITING_PREPARATION，tick实测只等待，无模型/发送。用户完成一次root认证安装/登记/gate后，
  后台自动初报；当前聊天核对上述安装哈希及精确task白名单后可decide execute_contract并tick一次。
  执行后使用`sudo -n -- /usr/local/lib/aegl-bridge/run_registered_task --diagnostic-summary --task-id
  CAL-WORD-PARAGRAPH-DIAG-001`读取元数据并记录，无需再让用户认证读日志。摘要读取本身不执行Hermes。
  真实SUCCESS+清理/回传确认后，host_acceptance外部副本WordParagraphImportTests>=4全通过，核对源码
  差异/断言/源文档哈希才COMPLETE。失败保留真实诊断并停止，不补模型次数/预算/替代身份。
- 当前root安装、登记、诊断实证、Hermes和宿主验收均NOT_RUN，Windows NOT_RUN。准备等待总窗口1小时，
  不自动延长。下方“没有新授权”等为本轮新授权前的历史结论，不覆盖本节。

**scratch清单已核对（用户认证后自动读取）**：清单SHA-256
`511019cbf32db45020b16b3043a99d6c0b77313a90218c7c00f5a92eab237f37`，51字节，
仅含scratch根目录及一个2975字节、0600的`hermes-snap-e4d68d5c0ce9.sh`普通文件，未列出子目录。
只读核对当前锁定Hermes源码：BaseEnvironment使用此命名，LocalEnvironment构造时init_session
捕获shell环境并原子发布快照。因此残留与终端初始化相符，不能据此证明模型响应或业务工具执行成功，
也无法确定超时位置；未读取或执行快照内容，未新增sudo请求。已完成的清单检查不再重复通知。
根因仍UNKNOWN；现有可读执行证据排查收口。下一次真实执行需要新的适用执行授权，并启用已有阶段
诊断以保留可定位证据；不能凭本次清单重放身份、加预算或创建替代任务。当前后台只等待新授权待办。

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
