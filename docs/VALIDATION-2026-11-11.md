# 2026-11-11 系统定点验证与使用入口改善

## 范围与基线

在两个已批准外部副本的 `feat/system-usage` 分支工作：

- AEGL 基线 `80506d66e0c0cf587288f296cc79dd3dc41c61eb`。
- Stack 基线 `39b2b00312b2f2f7da96576bef1bd0a156e21efd`。

本轮验证的是普通用户入口、只读健康查询、契约生成接线及教程可用性。
不重开已验收的 r10／观测部署／P0，不重放 001–008，不启动付费模型、设备、
sudo、安装、推广、消息发送或 campaign。没有创建 009。

## 实际修正

1. `bridge_cli.py::_cmd_status` 原先调用 `load_state()`，会创建缺失状态目录、
   初始化新链，并尝试 chmod 已有目录。改为只读打开既有 `state.json`；缺失时
   返回 `STATE_ABSENT`／rc=1，非法 JSON／非对象继续返回 ERROR，不修复文件。
   保留既有成功输出格式，不改 round／恢复／执行路径的初始化行为。
2. 首次 wrapper 安装器的固定哈希仍为旧 `f97b8f26…`，与基线自带的 wrapper
   不一致。更新为当前源码 SHA256
   `5ed0b06db96b48297e562277149b0e7f66d0314c96279c6d7e2365b772a9c5ca`。
   这是源码 pin 对齐，不是 root 安装成功证明；已有安装未改。
3. 删除 bootstrap 用法注释中 parser 没有实现的 `--keep-web-ui`。
4. 新增 Stack 首页和两仓中文操作说明，旧 Hermes S1 页面指向当前教程；
   AEGL 首页纠正过时的项目内 continuity／Beads 默认运行路径。

## 实际检查结果

| 检查 | 结果与能证明的范围 |
|---|---|
| `test_status_readonly.py` | 4 tests PASS；实际 CLI 子进程在隔离目录运行 |
| 状态缺目录／空目录 | rc=1、STATE_ABSENT；不建链、不改目录权限 |
| 状态与 journal／pending 已有 | rc=0；文件字节和模式、目录模式不变 |
| 状态损坏／JSON 非对象 | rc=1、ERROR；内容不修复，不产生新文件 |
| `test_bootstrap_dryrun.py` | 2 tests PASS；pin 被解析，隔离 XDG／Hermes 目录未创建 |
| 三个契约 CLI 连续调用 | manifest 8 entries；contract 1 requirement／1 task；READY，五类 gate PASS、errors=0 |
| 契约练习清理 | 按已知源文件及五个生成文件逐个删除、逆序 rmdir，成功；未使用递归强制删除 |
| 教程代码与链接 | 6 个本地文档链接有效；11 个 Bash 块语法通过，2 个嵌入 Python 块可编译；浏览器恢复／附着块没有执行 |
| wrapper 安装器源码 pin | 与 wrapper 实际文件 SHA256 一致；bash 语法通过；root 路径 NOT_RUN |
| AEGL help／version | 成功，版本 `1.4.0-dev` |
| model-config help／installed validate | 成功，配置格式为 openai-chat-completions；未访问上游和凭据值 |
| 安装的 registry CLI help | 成功，实际位置为 `/usr/local/lib/aegl-model-task/bin/aegl-model-task` |
| recovery doctor | REQUIRED_MISSING=0，OPTIONAL_MISSING=2（Docker、Maestro），Hermes pin MATCH |
| 当前 Bridge 查询 | WAITING_FOR_GPT，seq=13，pending=false，已消费身份数 12 |
| 当前 Bridge 查询前后 | 对 state／journal／pending／lock 的既有成员比较，字节与模式不变 |
| 当前安装对齐 | launcher、model broker、wrapper 分别与已验收源码逐字节哈希一致；未安装本轮新修改 |

测试均使用 `-B`／`PYTHONDONTWRITEBYTECODE=1`；新 status 测试成功按明确文件清单
清理，失败会保留场景。这里的测试结果不是 root、bwrap 或真实模型的新验收。

## 当前真实运行阻断／限制

- 专用 CDP `127.0.0.1:9333` 查询不可达（URLError）。Harness 的 socket／pid 文件
  存在，pid 对应进程存活，但这不证明 CDP 健康。没有进入正式 adapter 附着，
  所以 composer／login 状态 UNKNOWN。本轮没有恢复或重启浏览器。
- systemd 只读查询发现 enabled 的 `aegl-promote-broker.service` 与
  `aegl-entry-bind.target`；没有发现专用 Chrome／Harness 的持久自启 unit。
  普通 Chrome transient scope 不等于自启服务。
- 安装的 Harness 中 `BH_REQUIRE_EXISTING_DAEMON` 在 CLI `run.py` 路径判断；
  正式 adapter 直接调用的 `admin.ensure_daemon()` 本身可能恢复 daemon。
  因此教程不把整段正式附着说成“完全无状态动作”。未改上游包。
- 全量 layout gate **FAIL**，rc=1、violations=8。五个缓存目录共 19 文件的
  mtime 均早于本轮分支 ref 的创建时间，未删除；三处宿主路径仍存在：

  ```text
  scripts/lib/__pycache__
  specification/compiler/__pycache__
  specification/tests/__pycache__
  orchestration/hermes/supervisor/__pycache__
  orchestration/hermes/bridge/__pycache__
  orchestration/hermes/bridge/projects.py:41
  orchestration/hermes/bridge/tests/test_binding_wiring.py:209
  orchestration/hermes/bridge/tests/test_projects.py:24
  ```

  `projects.py` 的受信项目绑定仍包含本机身份与路径。本轮没有为使门禁变绿而
  扩大 allowlist、清未知缓存或绕过 layout；没有运行 `--no-layout` 当全量通过。
- 跨机首次部署尚不具备一键完成证明。旧基础模型安装器未包含两个 observer 模块，
  且存在旧递归清理；本轮不执行、不包装成完整安装方案。现有宿主观测部署的历史
  验收继续有效。

## 未执行与后续边界

没有全量离线 GATES=PASS，没有新增 root／bwrap、真实模型或 Android 设备验收；
没有变更宿主服务、代理、证书、凭据、registry、Bridge、正式树或旧任务结果。
完整系统不能仅凭这批定点 PASS 宣称全部就绪。

当前可直接使用的是中文教程的普通用户检查与离线契约练习。下一次真实受控任务
要先在明确授权下恢复专用浏览器，并通过正式 adapter 结构复核；新业务任务还需
自己的受信准备与一次执行授权。新源码的正式推广／安装另走现有可信路径。
