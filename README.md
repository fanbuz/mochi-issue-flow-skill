# Mochi Issue Flow Skill

[English](README.en.md)

Mochi Issue Flow 是一个面向 AI agent 的 **issue 动作工作流 SOP skill**。它将需求确认、跨仓协作、状态恢复、任务交接和验收收口统一到一个可持久化的 issue-like carrier 上，使协作状态能够被读取、恢复、同步和追踪。

这里的 **issue** 是一个通用概念，不限于 GitHub Issue。任何能够保存正文、评论、链接、状态和检查项的对象，都可以作为工作流载体：

- Gitea issue
- GitHub issue
- Linear issue
- Jira ticket
- 工作流任务
- 项目管理卡片
- 其他具备持久正文、评论和状态能力的系统对象

## 适用场景

Mochi Issue Flow 适用于需要通过 issue-like carrier 组织协作状态的场景：

- 单仓任务需要形成稳定的当前态、下一步和验收口径
- 一个 issue 需要另一个仓库、团队或 agent 提供支撑
- 多仓任务需要按阶段推进，并在阶段之间设置进入、退出和回滚条件
- 已存在的协作任务需要从 issue 正文、评论和链接中恢复上下文
- 交接给其他 agent 时，需要生成自解释的 handoff package
- 任务关闭前，需要核对提交、验证、关联 issue、验收结论和状态一致性

## 核心模型

Mochi Issue Flow 将协作任务分为三个层级：

| 层级 | 场景 | 载体策略 |
|------|------|----------|
| L1 单载体任务 | 当前仓库或当前任务可以独立闭环 | 使用当前 issue-like carrier 保存状态，不额外创建关联 issue |
| L2 关联 issue 流程 | 一个来源载体需要一个目标仓库、团队或 agent 支撑 | 创建一条双向关联 issue，并保持 source 与 target 互链 |
| L3 分阶段 flow | 多仓、多阶段、多条关联线，或需要 contract / phase gate | 创建 tracking issue，并只在当前阶段创建必要的关联 issue |

在 L2 和 L3 场景中，issue-like carrier 是工作流状态的权威来源。registry、dashboard、本地笔记和可视化页面都只能作为缓存或投影。

## 用户交互原则

Mochi Issue Flow 要求 agent 先用用户能直接理解的语言表达工作状态，再在需要时暴露协议字段。

用户主阅读路径应包含：

- 当前任务是什么
- 当前处于什么状态
- 当前责任人是谁
- 下一步动作是什么
- 是否存在阻塞
- 关联载体在哪里
- 什么条件下可以验收或关闭

协议字段如 `flowId`、`linkId`、`contractId`、`phase` 可以保存在 issue 正文或详情区中，但不应替代面向用户的当前态说明。

## 安装

将 `mochi-issue-flow/` 复制到支持 Agent Skills 的目录：

```bash
cp -R mochi-issue-flow ~/.codex/skills/
cp -R mochi-issue-flow ~/.claude/skills/
cp -R mochi-issue-flow ~/.agents/skills/
```

如果多个运行时共享同一套 skill，建议使用 `~/.agents/skills/`。

## 目录结构

```text
mochi-issue-flow-skill/
|-- README.md
|-- README.en.md
|-- VERSION
`-- mochi-issue-flow/
    |-- SKILL.md
    |-- agents/
    |   `-- openai.yaml
    `-- references/
        |-- carrier-model.md
        |-- exceptions.md
        |-- gitea-cli.md
        |-- templates.md
        `-- testing.md
```

## 主要能力

- **意图识别**：根据用户输入、issue 链接、仓库信息和已有状态判断 L1 / L2 / L3 / 只读路线。
- **当前态恢复**：从 carrier 正文、决定性评论、标签、检查项和 registry 缓存中恢复工作状态。
- **关联 issue 建立**：为跨仓或跨团队协作创建 source / target 双向链接。
- **分阶段推进**：通过 tracking issue 管理 phase、contract、gate 和当前责任人。
- **异常处理**：处理缓存不一致、状态过期、协议版本不兼容、阶段门未通过、合法暂停和 L2 升级 L3。
- **交接与收口**：输出 handoff package，并在关闭前核对验证证据、关联载体和验收结论。

## Gitea 与 gitea-cli

Mochi Issue Flow 是 carrier-neutral 的 skill，不依赖特定 issue 平台。一个常见落地方式是使用 Gitea issue 作为载体，并通过 `gitea-cli` 读取 issue、创建关联 issue、写入评论和回填状态。

Gitea 相关建议位于 `mochi-issue-flow/references/gitea-cli.md`。该文件只包含通用命令形态和安全默认值，不包含私有主机、组织、仓库或访问凭据。

## 使用示例

建立关联 issue：

```text
这个问题需要另一个仓库配合，请建立关联 issue。
```

恢复既有任务：

```text
继续处理这个 issue，先恢复当前状态。
```

建立多阶段协同：

```text
这个改造涉及多个仓库，需要按阶段推进并设置验收门槛。
```

## 安全与脱敏

本仓库只包含通用 skill、模板和参考资料。公开内容不应包含：

- 本地仓库路径
- 私有域名或内部服务地址
- 访问令牌、密钥或账号凭据
- 内部 issue 编号或私有项目名称
- 客户、员工、薪资、考勤等敏感业务数据

在复用或扩展本 skill 时，应将平台配置、私有仓库映射、内部标签体系和组织流程保存在私有发行版或本地配置中。
