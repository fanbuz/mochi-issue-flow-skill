# Mochi Issue Flow

[English](README.en.md) · [安装](#安装) · [快速开始](#快速开始) · [协议 30](#l3-flow-card-协议) · [贡献](CONTRIBUTING.md)

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Protocol](https://img.shields.io/badge/protocol-3.0-7c3aed.svg)](mochi-issue-flow/references/flow-card-schema.md)
[![Skill](https://img.shields.io/badge/Agent%20Skill-carrier--neutral-0f766e.svg)](mochi-issue-flow/SKILL.md)
[![Tests](https://img.shields.io/badge/tests-offline%20fixtures-0ea5e9.svg)](mochi-issue-flow/tests)

Mochi Issue Flow 是面向 AI agent 的开源协作 skill：它把 issue、ticket、任务卡等持久化对象变成可恢复、可审计、可交接的工作流载体。它既能处理单仓任务，也能让多个仓库、多个 agent 在同一个可验证的当前态上协作。

它不是某个公司或某个 issue 平台的流程副本。GitHub Issues、Gitea、Linear、Jira，以及任何能保存正文、评论、链接和状态的载体都可以接入。

## 它解决什么问题

- 任务换 agent 后，不必靠聊天记录猜测“现在做到哪一步”。
- 跨仓协作不再只有零散评论：source、support、driver、验收人与下一步都可追踪。
- 多仓验收不把“某仓有提交”误当作完成：它要求完整的 artifact commit set 与代码/运行态双轴证据。
- 重试、并发 agent 与状态回填不会彼此覆盖：卡片显式声明租约或 revision-only 并发模式。
- issue 是权威源，registry/看板是绑定 revision 的缓存；同步失败会显式变为待批准或不同步。
- 状态查询可以直接读取 canonical comment 的紧凑摘要，不必加载完整评论历史。
- 带属性或无属性的 sentinel 都会被精确解析；歧义输入停止处理，不会退回抓取任意 JSON。
- canonical comment 更新使用 revision/hash 前置条件和写后回读，平台不支持原生 CAS 时会明确标记残余竞态。
- 按只读、写入、迁移、关单和故障诊断分别限制实际加载工作集，正常运行脚本不读取源码。

## 核心模型

| 路线 | 何时使用 | 最小产物 |
|---|---|---|
| L1 单载体 | 一个仓库或一个 owner 可以闭环 | 当前态、下一步、验收证据 |
| L2 关联协作 | source 需要一个 support 仓库/团队/agent | 双向链接与交接包 |
| L3 Flow Card | 多仓、依赖 DAG、阶段门、并行 agent 或正式验收 | 跟踪载体中的一条规范状态评论 |

所有路线都遵循同一条规则：**载体当前态是权威源，缓存只是投影。** L3 将这一当前态结构化为 Flow Card。

## 安装

将整个 `mochi-issue-flow/` 目录复制到运行时可发现的 skills 目录。不要只复制 `SKILL.md`；模板、参考资料、校验器和测试夹具属于同一个发布单元。

```bash
cp -R mochi-issue-flow ~/.codex/skills/
cp -R mochi-issue-flow ~/.agents/skills/
cp -R mochi-issue-flow ~/.claude/skills/
```

如果多个 agent 运行时共用一套能力，推荐把同一版本安装到 `~/.agents/skills/`，并由同步脚本或包管理流程维护，而不是人工复制不同版本。

## 快速开始

### 1. 让 agent 先路由，不要先写 issue

```text
这个任务涉及两个仓库，先恢复已有 issue 的当前态，再决定是否建立 L3 Flow Card。
```

skill 会读取载体正文、关联载体和最新决定性评论，将工作归入 L1、L2、L3 或只读路线。创建关联 issue、转移所有权、暂停和关闭前都应取得用户确认。

### 2. L2：发起一个可验收的支撑请求

```text
这个 issue 需要前端仓库支持。请建立双向关联，并生成可直接交给 support agent 的交接包。
```

使用 `templates/delivery-packet.json` 将目标、权威 carrier、期望证据、完整 artifact set 与幂等键交给另一个 agent。人类可读说明可以附带，但不替代这个包。

### 3. L3：对多仓工作建立一条 Flow Card

在跟踪 issue 中创建 `templates/flow-card-comment.md` 的评论。首次创建时 `canonicalStatusCommentUrl` 为 `null`；获得评论 URL 后，立即**编辑同一条评论**回填 URL 并将 `statusRevision` 加一。以后只编辑这一条当前态评论。

```bash
python3 mochi-issue-flow/scripts/validate_flow_card.py flow-card.json
python3 mochi-issue-flow/scripts/audit_flow.py flow-card.json
python3 mochi-issue-flow/scripts/audit_flow.py --mode closeout flow-card.json
```

第一个命令验证结构；第二个命令执行日常审计；第三个命令返回显式 `closeoutEligible`。错误或不可关单会以退出码 `2` 结束，适合自动化 gate 使用。

已有 canonical comment 的更新先准备 revision/hash 前置条件，平台原地编辑后再回读验证：

```bash
python3 mochi-issue-flow/scripts/conditional_comment_edit.py prepare request.json live-snapshot.json --now 2026-07-16T10:00:00Z
python3 mochi-issue-flow/scripts/conditional_comment_edit.py verify request.json saved-snapshot.json
```

## L3 Flow Card 协议

Flow Card 是嵌在权威评论中的 JSON，由 HTML sentinel 包围，便于人和脚本同时阅读：

````md
<!-- flow-card:start v3 -->
```json
{ "protocolVersion": "3.0", "statusRevision": 7 }
```
<!-- flow-card:end -->
````

完整字段见 [schema](mochi-issue-flow/references/flow-card-schema.md) 和 [模板](mochi-issue-flow/templates/flow-card-comment.md)。关键约束如下。

| 概念 | 约束 |
|---|---|
| 单一权威评论 | `canonicalStatusCommentUrl` 指向唯一当前态；首次创建后回填该 URL。 |
| 紧凑状态读取 | 摘要由 canonical JSON 生成并绑定 `sourceStatusRevision` 与内容哈希。 |
| 条件修订 | `statusRevision` 每次成功编辑递增；写入前检查 revision/hash 与 lease owner，写后回读目标 revision/hash。 |
| Bridge | 每个跨仓工作单元都有稳定 `bridgeId`，并用依赖 DAG 表达先后关系。 |
| 完整提交集 | `currentCommit` 与 `acceptedCommit` 都必须覆盖该 Bridge 的全部 `relevantArtifactRepos`。 |
| 双轴验收 | `codeState` 与 `runtimeState` 分别验证；仅被标为 required 的轴阻塞完成。 |
| 提交漂移 | 两个提交集不一致时，活跃证据转入 `supersededEvidence`，required 轴进入 `needs-reverify`。 |
| 历史归档 | 先写入并校验不可变归档，再用 `archiveRefs` 替换活跃卡中的冗长历史。 |
| 并发保护 | `lease` 为旧 V3 默认；显式单写入者可使用 `revision-only`。 |
| Registry | `synchronized` 必须绑定当前 `lastSyncedStatusRevision`；批准的 waiver 是唯一关单例外。 |

协调状态（例如 `ready-for-acceptance`）不能替代 `flowCodeState` 与 `flowRuntimeState`。只有 closeout 审计确认 required 轴和同步门禁全部满足，才可进入最终完成。

状态查询使用 `scripts/flow_status.py`；条件写入使用 `scripts/conditional_comment_edit.py`；证据归档使用 `scripts/archive_flow_evidence.py`；上下文预算使用 `scripts/check_context_budget.py`。平台 adapter 必须在结果进入模型前完成 comment 定向过滤，并只返回一份规范化载荷。例行执行直接运行脚本，只有脚本自身失败且需要实现诊断时才读取源码。

## Token 消耗与优化点

Mochi Issue Flow 的设计目标不是把完整 issue 历史塞进上下文，而是把“当前态”压缩成可验证的最小工作集。一次只读状态查询应优先读取 canonical comment，并用 `scripts/flow_status.py` 生成绑定 `sourceStatusRevision` 和内容哈希的紧凑摘要；正常目标是控制在约 3,000 tokens 以内。一次常规 L3 恢复在进入业务代码或仓库上下文前，应尽量控制在约 8,000 到 10,000 tokens。

主要优化点：

- 路由先行：先判断 Read-only / L1 / L2 / L3，只加载该路线必需的 reference。
- 精确载体读取：adapter 只返回 canonical comment 或目标评论，不把完整评论历史交给模型筛选。
- 脚本优先：状态摘要、审计、条件写入、归档和预算检查直接运行脚本；只有脚本失败且需要实现诊断时才读取源码。
- 当前态优先：Flow Card 保留活跃证据和必要门禁，冗长旧证据通过归档引用迁出。
- 预算可审计：`scripts/check_context_budget.py` 使用规范化 JSON 字符数作为无依赖硬指标；如果环境安装了 `tiktoken`，会额外报告 `o200k_base` token 估算。

更详细的阈值、fixture 和 CI 口径见 [context budget](mochi-issue-flow/references/context-budget.md)。

## 使用正确的工作区

跨仓验证前，记录每个相关仓库的路径、分支、worktree 与 SHA。独占、干净的专用分支可直接使用；共享分支、并行 agent 或需要独立索引时使用 worktree。

新 worktree 不会自动带入被 Git 忽略的本地 skill、配置或生成文件。将所有必需文件是否 materialize 作为 preflight gate；任何缺失都应阻止验证，而非让 agent 用部分协议继续。详见 [workspace preflight](mochi-issue-flow/references/workspace-preflight.md)。

## 验证与测试

核心校验与审计器仅依赖 Python 标准库，且只读取离线 JSON。载体 API（GitHub、Gitea、Jira 等）的读取和写入属于 adapter 层，因此单元测试可重复，不依赖网络或远程分支。

```bash
python3 -m unittest discover -s mochi-issue-flow/tests -p 'test_*.py' -v
```

在发布仓根目录运行时，测试还会校验 README、许可证、版本和缓存忽略规则；安装到 skills 目录后，这些仓库级检查会明确跳过，Flow Card、模板与审计器的核心测试仍可独立运行。

场景与证据要求见 [S1–S4 矩阵](mochi-issue-flow/references/scenario-evidence-matrix.md)。在关闭 L3 Flow 前使用 closeout 模式审计：状态缺失、提交漂移、registry revision、租约停滞和全部 required 轴。

## 目录结构

```text
mochi-issue-flow-skill/
├── LICENSE                         # Apache-2.0
├── NOTICE
├── README.md / README.en.md
├── CONTRIBUTING.md
├── VERSION
└── mochi-issue-flow/
    ├── SKILL.md                    # 精炼的 agent 入口
    ├── agents/openai.yaml
    ├── templates/                  # Flow Card、issue、证据、交接包
    ├── references/                 # schema、状态、租约、预检、场景
    ├── scripts/                    # 离线状态、validate、audit、归档与预算
    └── tests/                      # 可重复 fixture 测试
```

## 安全与隐私边界

公开版只保存通用协议与模板，严禁写入本地路径、内部域名、私有仓库、issue 编号、访问令牌、账号、客户数据或任何业务敏感信息。项目专属的 adapter、标签、仓库映射和审批规则应留在私有配置或项目内适配层。

## 许可证

本项目采用 [Apache License 2.0](LICENSE)（SPDX：`Apache-2.0`）。它允许商业使用、修改和再分发，并明确包含贡献者专利授权；保留许可证、NOTICE 与必要变更声明即可。商标使用不因许可证获得授权。

## 贡献

欢迎通过 issue 或 pull request 改进协议、模板和 adapter 边界。提交前请运行离线测试，保持 `SKILL.md` 精炼，并确保新增内容不包含私有上下文。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。
