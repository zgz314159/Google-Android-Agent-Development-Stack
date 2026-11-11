# AEGL／Stack 系统使用教程

核对日期：2026-11-11。本文针对 Linux 当前实现。
它区分本机已有受控安装与另一台机器首次部署；标为“示例／未执行”的命令不会
因为出现在教程中就获得发送、模型调用或 root 安装授权。

## 1. 先理解系统

```text
需求 → 作者输入 → Stack 离线编译器 → 冻结契约 + READY
                                      ↓
固定 ChatGPT 控制会话 ← Browser-Harness ← Bridge 单轮协议
                                      ↓
root 受控 wrapper → AEGL 沙箱／模型 broker → Hermes
                                      ↓
外部工作区中的结果 → 确定性检查 → 结果回传与业务验收
```

- AEGL 仓：治理、独立身份、只读正式树、任务登记、沙箱和可信推广。
- Stack 仓：契约、Bridge、有限 campaign、验证与评估。
- Hermes：安装的上游执行内核；受控链路通过 AEGL broker 使用模型服务。
- 专用 Chrome + Browser-Harness：传输控制消息，不是模型或任务执行器。
- ImageAnalysisFactory、KeepLab 是业务项目，不能用它们的名称代替系统名称。
- `aegl status` 是项目交接状态；`bridge_cli.py status` 是控制链状态，二者不同。

READY 证明契约通过静态门禁；guard 是前置授权；hook 是诊断。
这些都不能单独证明工具成功或业务验收通过。缺历史记录时写 UNKNOWN。

## 2. 当前机器的目录与身份

| 对象 | 当前实例 | 使用者 |
|---|---|---|
| AEGL 外部开发副本 | `/var/tmp/IAP-CONTROL-DEV/aegl` | zhong |
| Stack 外部开发副本 | `/var/tmp/IAP-CONTROL-DEV/stack` | zhong |
| 正式系统源码 | `/home/zhong/Projects/` 下两个系统目录 | AI 只读，推广走 broker |
| 沙箱与模型 broker 安装 | `/usr/local/lib/aegl-model/` | root 管理 |
| 受控 wrapper | `/usr/local/lib/aegl-bridge/run_registered_task` | root |
| 模型任务登记 CLI | `/usr/local/lib/aegl-model-task/bin/aegl-model-task` | register 要 root；查询按实际权限 |
| Bridge 状态 | `~/.local/state/google-android-agent-stack/bridge` | zhong |
| Supervisor 状态 | `~/.local/state/google-android-agent-stack/supervisor` | zhong |
| 专用浏览器状态 | `~/.local/state/google-android-agent-stack/browser` | zhong |
| 模型任务 registry | `/var/lib/aegl-model/registry.json` | root 登记 |
| 模型运行身份 | `aegl-ai` | 由受信入口降权进入沙箱 |

`scripts/lib/stack_paths.py` 是 Stack 路径契约。可设置
`ANDROID_AGENT_STACK_{STATE,DATA,CACHE,CONFIG}_ROOT`；Bridge 另有
`HERMES_BRIDGE_STATE_DIR`。日常查询必须使用同一个正确状态目录，不能因换 HOME
误看另一条链。不要把 root 的 HOME 用于 Chrome、Harness、Bridge 或 campaign。

## 3. 本机最短日常路径：先只读检查，再决定是否执行

在 zhong 的普通终端运行，**不用 sudo**：

```bash
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1
AEGL=/var/tmp/IAP-CONTROL-DEV/aegl
STACK=/var/tmp/IAP-CONTROL-DEV/stack
export HERMES_BRIDGE_STATE_DIR="$HOME/.local/state/google-android-agent-stack/bridge"

# 工具、路径与 Hermes pin；没有模型调用。
PROJECTS_ROOT="$HOME/Projects" bash "$AEGL/bin/aegl-recovery" doctor

# 当前模型路由格式检查；不读取凭据值、不发网络请求。
/usr/local/bin/aegl-model-config validate

# 新分支已修正为只读：缺状态返回 STATE_ABSENT，不初始化新链。
python3 -B "$STACK/orchestration/hermes/bridge/bridge_cli.py" status |
  python3 -c 'import json,sys; d=json.load(sys.stdin); s=d.get("state",{}); print(json.dumps({"decision":d.get("decision"),"status":s.get("status"),"sequence":s.get("expected_sequence"),"pending":d.get("pending_result")},ensure_ascii=False))'

# 专用 CDP 是否可达；不读取聊天正文。
curl --fail --silent --show-error --max-time 3 http://127.0.0.1:9333/json/version |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["Browser"])'
```

逐项检查退出码；不要仅看最后一条命令。查询管道可先 `set -o pipefail`，以保留
左侧 CLI 的失败退出码。`STATE_ABSENT`、ERROR、pending 不为空、CDP 不可达，都先
停下定位。不要自动初始化、清状态、recover 或重发来获得绿色输出。

本轮实测：工具 required 缺失数 0、Hermes pin 匹配、模型配置 validate 通过；
Bridge 为 WAITING_FOR_GPT、seq=13、pending=false。9333 不可达，所以**没有进行
正式 adapter 附着或登录判定**。以上是本轮快照，下一次仍需查询当前状态。

`aegl`、`aegl-task`、`aegl-model-task` 在本次 PATH 中没有同名命令；本文使用
已核对的绝对入口。不要为运行教程临时改系统 PATH 或放宽 sudoers。

## 4. 专用 Chrome 与 Browser-Harness

### 4.1 恢复前检查

本机专用地址是 `http://127.0.0.1:9333`，profile 是
`$HOME/.local/state/google-android-agent-stack/browser/chrome-profile`。
固定控制会话是 adapter 源码中的 `CONTROL_URL`；本机当前值：
`https://chatgpt.com/c/6ac4d058-acb8-83e8-bf2c-8bb4b8aa2278`。
另一账号／机器不能照抄这个私有会话身份，需先完成项目级绑定审查。

先用上节 CDP 查询。可达就复用；不可达时先确认该专用 profile 是否还有进程占用。
若已有进程占用而连接失败，保留现场并处理网络／浏览器状态；不要再启动第二份。
只有确认专用进程不在运行且本次允许恢复时，才在普通图形会话终端执行：

```bash
# 一次性恢复示例；本轮未执行。不要加 sudo。
BROWSER="$HOME/.local/state/google-android-agent-stack/browser"
PROFILE="$BROWSER/chrome-profile"
CONTROL_URL=https://chatgpt.com/c/6ac4d058-acb8-83e8-bf2c-8bb4b8aa2278
mkdir -p "$BROWSER"
umask 077
nohup google-chrome \
  --remote-debugging-address=127.0.0.1 --remote-debugging-port=9333 \
  --user-data-dir="$PROFILE" "$CONTROL_URL" \
  > "$BROWSER/chrome.log" 2>&1 < /dev/null &
```

随后只做一次 CDP 复核。命令启动成功不等于页面加载、登录或 adapter 已通过。
已有固定会话时不要再次把 CONTROL_URL 作为启动参数，否则可能增加重复标签。
不删除 SingletonLock/socket/pid，不使用 `--ignore-certificate-errors`。

### 4.2 Harness 恢复与正式附着

先确认 Chrome 的 CDP 已恢复，再恢复 Harness。它属于 Hermes 安装的依赖，不用
系统 Python 临时 pip 一份，也不固定一个可能被上游 GC 的旧 venv 路径。
本机已核对 launcher 支持 `--print-runtime-command`，可取得该安装的 store Python：

```bash
HERMES_PY=$(hermes --print-runtime-command |
  python3 -c 'import json,sys; print(json.load(sys.stdin)[0])')
test -x "$HERMES_PY"
export HERMES_HOME="$HOME/.hermes"
export BU_NAME=hermes-chatgpt
export BU_CDP_URL=http://127.0.0.1:9333
export BH_HOME="$HOME/.local/state/google-android-agent-stack/browser/browser-harness"
export BH_RUNTIME_DIR="$BH_HOME/runtime"
unset BU_CDP_WS
```

只有允许恢复 daemon 时，执行一次下面的**恢复动作**，不是只读检查：

```bash
# 本轮未执行；ensure_daemon 可能重建 daemon／runtime，或创建 about:blank 标签。
RECOVER_CODE=$(cat <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/'.hermes/hermes-agent'))
import hermes_bootstrap
from browser_harness.admin import ensure_daemon
ensure_daemon()
print('ENSURE_DAEMON_OK')
PY
)
env -u BH_REQUIRE_EXISTING_DAEMON "$HERMES_PY" -I -c "$RECOVER_CODE"
```

恢复失败立即停止，不手工删除 pid/socket。当前安装的 `ensure_daemon()` 会做真实
CDP 健康探测，可能恢复陈旧 daemon；因此不能把调用它说成“完全没有状态动作”。
正式 adapter 自己设置 `BH_REQUIRE_EXISTING_DAEMON=1`。本次安装中，该变量在 Harness
CLI 的 `run.py` 路径判断；adapter 还直接调用 `admin.ensure_daemon()`，不能仅凭
这个环境变量声称正式附着绝不恢复进程。调用方不要用另一份 Harness 绕过拒绝。

在 Chrome 与 Harness 均恢复后，用正式 adapter 做结构复核（本轮未执行；除标签
切换外，它仍会经过上面的 ensure 路径，不能声称整个附着过程完全没有状态动作）：

```bash
CHECK_CODE=$(cat <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import chatgpt_adapter as a
try:
    ops = a.RealOps()
    tab = ops.find_control_tab()  # 要求固定 URL 恰好一个标签；可能切换到该标签。
    state = ops.js("""(() => ({
      error_page: location.href.startsWith('chrome-error:'),
      composer: !!document.querySelector('[contenteditable="true"][role="textbox"]'),
      login: !!document.querySelector('a[href*="/auth/login"],button[data-testid="login-button"]')
    }))()""")
    state = dict(state) if isinstance(state, dict) else {}
    ok = not state.get('error_page', True) and state.get('composer') is True and state.get('login') is False
    print(json.dumps({'adapter':'OK' if ok else 'NOT_READY','url':tab.get('url'),
      'title':tab.get('title'),'structure':state},ensure_ascii=False))
    raise SystemExit(0 if ok else 1)
except a.AdapterError as exc:
    print('ADAPTER=FAIL category='+type(exc).__name__)
    raise SystemExit(1)
PY
)
"$HERMES_PY" -I -c "$CHECK_CODE" "$STACK/orchestration/hermes/bridge"
```

此片段不调用 conversation_text，不读取正文、不填写或发送。若没有 composer，
不要把它直接当登录失败：加载错误页的登录状态为 UNKNOWN。
重复标签时停止；确认两个都是错误页并有本次操作授权后，才关闭一个、保留固定
会话并刷新一次。登录页交给用户登录；再次加载失败就停止，不循环刷新／重启。

### 4.3 是否随重启自动运行

本轮 systemd 查询只找到 `aegl-promote-broker.service` 与 `aegl-entry-bind.target`
为 enabled；没有找到专用 Chrome 或 Harness 的持久自启 unit。普通 Chrome 的
transient scope 不是自启服务。源码、profile 和安装结果持久存在，不保证进程
跨重启仍在；下次从健康检查开始。不要杜撰 `systemctl start hermes`。

## 5. 不调用模型的最小契约练习

这一步可熟悉“输入 → manifest → contract → READY”。它是 FixtureApp 离线练习，
不会登记真实任务，也不是可以直接交给生产 Bridge 的业务包。

```bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
DEMO=$(mktemp -d /var/tmp/stack-contract-demo.XXXXXX)
git -C "$STACK" archive HEAD specification/tests/fixtures/valid_package |
  tar -x -C "$DEMO"
P="$DEMO/specification/tests/fixtures/valid_package"
C="$STACK/specification/compiler"
python3 -B "$C/hash_manifest.py" "$P"
python3 -B "$C/build_contract.py" "$P"
python3 -B "$C/validate_package.py" "$P" --project-root "$P/project"
# 必须 STATUS=READY，五类 gate 全 PASS、errors=0；否则保留 DEMO 并停止。
printf 'DEMO=%s\n' "$DEMO"
```

该三入口链本轮实际运行通过。练习完成后，仅在确认无需保留时，按明确清单清理：

```bash
rm -- "$P/DESIGN.md" "$P/PRODUCT.md" "$P/acceptance.md" "$P/design.md" \
  "$P/project-context.json" "$P/requirements.md" "$P/tasks.md" \
  "$P/verification-intent.json" "$P/project/app/Main.kt" \
  "$P/manifest.json" "$P/implementation-contract.json" "$P/EXECUTOR-PROMPT.md" \
  "$P/validation-report.json" "$P/READY.json"
rmdir -- "$P/project/app" "$P/project" "$P" \
  "$DEMO/specification/tests/fixtures" "$DEMO/specification/tests" \
  "$DEMO/specification" "$DEMO"
```

出现未知文件或清理失败时保留现场，不能改用递归强制删除。

## 6. 一次真实任务的顺序

当前没有“任意项目名 + 一句话就安全执行”的通用一键入口。按以下顺序走：

1. **明确业务与受信绑定。** `bridge/projects.py` 目前只声明 Stack 与
   ImageAnalysisFactory。新业务项目必须先有经过审查的项目绑定，不能把现有
   IAP 包直接改个任务号。Stack 控制平面的自修改任务还会被专门门禁拒绝。
2. **作者输入与契约。** 在项目拥有的外部工作副本编写八个作者输入，使用第 5 节
   三个编译器入口生成产物。修正输入或生成器，不手改生成后的冻结产物。
3. **受信准备，尚无模型。** root 控制器分配全新身份、可写 worktree/scratch，
   安装可信契约、核对 baseline/binding、登记、沙箱 `--check`、ready/live-state。
   `--check` 不调模型，但会准备沙箱，属于受信运行操作，不是普通状态查询。
4. **明确批准一次执行。** 从同一个已验证副本使用该任务自己的执行入口。
   `--execute` 不是 Bridge 的选项，是特定 delivery driver 的选项；001–008 已消费，
   不再执行、不创建 009。本轮没有给新任务分配身份，也没有替用户发送控制消息。
5. **Bridge 只消费一个合法任务。** 校验序号、nonce、回复链、风险、契约及登记；
   经安装 wrapper 与 AEGL 沙箱调用 Hermes，默认预算以该轮批准值为准。
6. **看三类结果。** 执行 exit/outcome、wrapper cleanup 确认、消息 send 确认，
   再看契约要求的业务证据。任一缺失不能用另一项代替。
7. **验收后才推广。** Git push 是上传源码；正式源码推广与 root 安装另走受信流程。

仅供已批准任务的入口示例，**本轮未执行**：

```bash
# zhong；会读控制会话，可能执行模型并回传结果，不能拿来做健康检查。
BU_CDP_URL=http://127.0.0.1:9333 \
  AEGL_HERMES_TASK_ID="$APPROVED_TASK_ID" \
  python3 -B "$APPROVED_STACK/orchestration/hermes/bridge/bridge_cli.py" round

# 查询已存在 campaign 不会运行它；使用实际已有 ID。
python3 -B "$STACK/orchestration/hermes/supervisor/campaign_cli.py" \
  status --campaign-id "$EXISTING_CAMPAIGN_ID"
```

`APPROVED_TASK_ID`、`APPROVED_STACK` 必须来自该轮受信准备，不能在本机随意指定
开发副本来取代正式受控执行链。不要手填旧 nonce、复用消费过的身份或修改阶段标记。
campaign `run` 可能发起多轮；普通首次操作优先采用已批准的一轮，不启动无限循环。

## 7. 另一台机器首次安装

**当前源码不具备已验证的跨机一键部署。** 可以先取得源码并做普通用户预演：

```bash
mkdir -p "$HOME/Dev"
git clone --branch feat/system-usage \
  https://github.com/zgz314159/AI-Engineering-Governance-Layer.git "$HOME/Dev/aegl"
git clone --branch feat/system-usage \
  https://github.com/zgz314159/Google-Android-Agent-Development-Stack.git "$HOME/Dev/stack"
AEGL="$HOME/Dev/aegl"
STACK="$HOME/Dev/stack"
PYTHONDONTWRITEBYTECODE=1 bash "$STACK/scripts/bootstrap-host.sh" --dry-run
```

这里克隆本轮的 `feat/system-usage` 工作分支，包含教程与查询修正；它仍需审查和
可信推广。取得源码不等于已经更新本机正式树或已安装组件。

最低普通工具为 Git、Bash、Python、Java、Node/npm、uv、pnpm、mise；受控执行另需
bubblewrap、setpriv、ACL、独立服务身份及 Linux namespace 支持。Android 验证另需
相应 SDK／设备／驱动；不连接设备不影响离线契约练习。

`bootstrap-host.sh` 的 dry-run 本轮验证无写入；真实 bootstrap **未执行**。
它准备锁定的 Hermes checkout、配置模板、Playwright 环境，真实运行会安装依赖；
它不完成 AEGL 身份、entry-bind、模型 broker、registry、sudoers、控制会话绑定。
其模板也不能直接等同于本机已安装的受控 profile。

首次受控部署仍需逐项审查：

- 目标用户、正式源码路径与 project binding；当前部分路径固定为本机 zhong。
- 独立 `aegl-ai`／broker／promotion 身份、只读入口挂载与受控 sudoers。
- Hermes 锁定版本及依赖；专用 Chrome 和 Harness 的本地 CDP 连接。
- 模型服务和模型 ID、credential **引用**的配置；由操作者本地完成认证，不把
  key 放进命令行或发到对话。模型路由格式通过不代表真实额度／鉴权通过。
- 完整候选依赖的 root 安装和隔离检查，最后才批准一次真实任务。

本轮发现旧 `install-model-broker.sh` 的基础安装清单没有两个 observer 模块，且
沿用旧清理实现；不要把它单独当成当前组合的一键安装器。已有宿主上的四文件部署
已经验收，不重开。本轮只对首次 wrapper 安装器的旧哈希作了源码对齐，root 安装
仍 NOT_RUN。也不要运行历史 GT1／IAP 报告里的固定旧 anchor 或阶段命令。

## 8. 常见失败：定位后停在哪里

| 现象 | 本次操作 |
|---|---|
| `command not found` | 核对第 2 节绝对入口；不临时下载另一版本绕过 |
| `STATE_ABSENT` | 核对 HOME／状态路径；不自动建新链 |
| 9333 refused | 按第 4 节检查专用进程，再决定一次恢复 |
| Harness 文件在但连接失败 | 文件存在不是健康证据；用正式 adapter 确认，失败停止 |
| 两个控制标签 | 不发送；确认页面类型，按一次性人工恢复流程处理 |
| 错误页／登录页 | 错误页不能判未登录；用户处理网络／登录；不关证书校验 |
| `NO_CONTROL_MESSAGE`／未验证任务块 | 本轮不执行；等待正确合法任务，不能编造任务块 |
| `SEND_UNCERTAIN` | 不盲目重发；依据已持久化 pending 和用户决策走已有 resolver |
| `RECOVERY_REQUIRED` | 保留 journal/pending；不能靠删除状态重新开始 |
| timeout／cleanup UNKNOWN | 本轮失败或未确认；不增加预算掩盖，不回填旧结果 |
| 契约／前驱／owner／权限不符 | 停在该门禁，报告实际 rc；不 chmod／force 修成通过 |
| layout gate 失败 | 保留并报告具体路径，不用 `--no-layout` 宣称全量通过 |

本轮只读诊断与离线检查的具体范围、剩余问题见
[定点验证记录](VALIDATION-2026-11-11.md)。
