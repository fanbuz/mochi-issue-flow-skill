# User-facing message filter and examples

Use these examples when authoring or reviewing Mochi instructions. Normal issue execution follows the short contract in `SKILL.md` and does not load this reference.

Every opening paragraph communicates the recognizable outcome, data impact, and stop/next point. Protocol evidence may follow, but the first paragraph does not begin with `L3`, `Flow Card`, `Bridge`, `lease`, `registry`, or scenario IDs.

## Visibility filter

| Internal event | Default user visibility | User-facing expression |
|---|---|---|
| Carrier read, status revision, content hash, or conditional edit | Hidden | Report only the resulting current state or a conflict that changes what can happen next. |
| Lease acquire, renew, heartbeat, or transfer | Hidden | Say who can continue only when ownership affects progress or needs a decision. |
| Registry/cache projection or file-format synchronization | Hidden | Say that the final status or deliverables are synchronized only when this is a meaningful result. |
| Code/runtime axis recalculation or validation pass | Hidden | State what has passed, what has not, and the concrete reason. |
| User data write, rollback, irreversible action, approval, blocker, or completion | Visible | State the practical effect, safety boundary, and next step. |

Aggregate adjacent internal events. One carrier update, a reread, a hash check, a cache sync, and another validation pass normally produce zero intermediate messages and one result update. Do not echo every transition, and do not repeat a result after recording its evidence.

For example, replace:

> Lease recovery passed, revision 18 was saved, the canonical hash is locked, the code axis is verified, and the runtime axis remains blocked. Next I will synchronize Markdown, XLSX, HTML, and the registry.

With:

> The previous result has been recovered and checked for consistency. The code change is accepted, but the integration environment still prevents completion; next I’ll work on that environment issue.

If the user explicitly asks for a protocol trace, give the plain-language result first, then a separate compact technical note. Never let the trace replace the result.

## Examples

| Situation | Chinese example | English example |
|---|---|---|
| Read-only check | 我先确认测试环境和本次验收数据是否可用。这一步只读取状态，不会修改数据或启动业务操作；确认后我会告诉你能否安全继续。 | I’ll confirm that the test environment and acceptance data are available. This is read-only and will not change data or start a business operation; I’ll report whether it is safe to continue. |
| Before a write | 下一步会更新现有排班数据，成功后会影响本月排班结果。我会先核对完整月份和当前版本，任一条件变化都会停止写入。 | The next step will update the existing schedule and may change this month’s result. I’ll verify the full month and current version first, and stop if either has changed. |
| Write succeeded | 排班已保存成功，事务已提交，后续核对可以继续。我接下来会验证读取结果与本次提交一致。 | The schedule was saved and the transaction committed, so verification can continue. I’ll now confirm that the saved result matches this submission. |
| Write failed | 排班没有保存成功，事务未提交，后续写入已经停止。下一步只诊断这次失败原因，不会继续修改排班。 | The schedule was not saved, the transaction did not commit, and later writes have stopped. The next step only diagnoses this failure and will not modify the schedule. |
| Waiting for approval | 接口失败但没有返回具体原因，我已停止后续写入。如果你允许，我只读取本机服务控制台中的这次异常，不操作服务或数据。 | The request failed without a specific cause, and I stopped later writes. With your approval, I’ll only read the matching local service error and will not operate the service or data. |
| Multi-step recovery | 上一阶段结果已恢复并通过一致性检查，代码变更已经验收；联调环境仍未通过，因此任务暂不能结束。下一步会继续处理环境问题。 | The previous result has been recovered and checked for consistency. The code change is accepted, but the integration environment still prevents completion; next I’ll work on that environment issue. |
| Closeout | 本次交付的代码和运行验收均已通过，没有剩余阻塞，可以关闭。关闭前我会保存最终证据并确认最终状态已同步。 | Code and runtime acceptance have passed with no remaining blocker, so the delivery can close. Before closing, I’ll preserve the final evidence and confirm that the final status is synchronized. |

When the user asks for protocol details, explain the technical terms after the outcome. Do not hide uncertainty, transaction state, approval scope, or irreversible impact behind simpler wording.
