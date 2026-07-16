# User-facing message examples

Use these examples when authoring or reviewing Mochi instructions. Normal issue execution follows the short contract in `SKILL.md` and does not load this reference.

Every opening paragraph communicates the recognizable outcome, data impact, and stop/next point. Protocol evidence may follow, but the first paragraph does not begin with `L3`, `Flow Card`, `Bridge`, `lease`, `registry`, or scenario IDs.

| Situation | Chinese example | English example |
|---|---|---|
| Read-only check | 我先确认测试环境和本次验收数据是否可用。这一步只读取状态，不会修改数据或启动业务操作；确认后我会告诉你能否安全继续。 | I’ll confirm that the test environment and acceptance data are available. This is read-only and will not change data or start a business operation; I’ll report whether it is safe to continue. |
| Before a write | 下一步会更新现有排班数据，成功后会影响本月排班结果。我会先核对完整月份和当前版本，任一条件变化都会停止写入。 | The next step will update the existing schedule and may change this month’s result. I’ll verify the full month and current version first, and stop if either has changed. |
| Write succeeded | 排班已保存成功，事务已提交，后续核对可以继续。我接下来会验证读取结果与本次提交一致。 | The schedule was saved and the transaction committed, so verification can continue. I’ll now confirm that the saved result matches this submission. |
| Write failed | 排班没有保存成功，事务未提交，后续写入已经停止。下一步只诊断这次失败原因，不会继续修改排班。 | The schedule was not saved, the transaction did not commit, and later writes have stopped. The next step only diagnoses this failure and will not modify the schedule. |
| Waiting for approval | 接口失败但没有返回具体原因，我已停止后续写入。如果你允许，我只读取本机服务控制台中的这次异常，不操作服务或数据。 | The request failed without a specific cause, and I stopped later writes. With your approval, I’ll only read the matching local service error and will not operate the service or data. |
| Closeout | 本次交付的代码和运行验收均已通过，没有剩余阻塞，可以关闭。关闭前我会保存最终证据并确认状态投影已同步。 | Code and runtime acceptance have passed with no remaining blocker, so the delivery can close. Before closing, I’ll preserve the final evidence and confirm the status projection is synchronized. |

When the user asks for protocol details, explain the technical terms after the outcome. Do not hide uncertainty, transaction state, approval scope, or irreversible impact behind simpler wording.
