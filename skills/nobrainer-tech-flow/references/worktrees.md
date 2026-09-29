# Task worktree lifecycle

Use one isolated Git worktree per repository task by default. This keeps the
owner's checkout and its uncommitted work untouched while giving the task a
fresh, verifiable base. An explicit owner instruction to work in a particular
checkout or branch overrides this default.

## Start from the current remote default

1. Inspect the repository, remotes, current checkout and dirty state. Record the
   original checkout's state; never reset, clean, stash, switch its branch, or
   copy its dirty files into the task worktree as a shortcut.
2. Discover the default branch from the remote's symbolic `HEAD` (for example,
   `refs/remotes/origin/HEAD`), then verify that it resolves to an existing
   branch on the intended remote. Fetch that branch and read back its commit
   after the fetch. Do not assume the branch is named `main` or `master`, and
   do not treat a stale local tracking ref as fresh evidence.
3. If the symbolic remote `HEAD` is missing or invalid, inspect the remote's
   advertised default-branch metadata and verify the selected branch with a
   readback. If the remote/default branch cannot be determined or fetched,
   report the concrete issue and stop before project writes; use another base
   only when the owner specifies it.
4. Create a uniquely named task branch and worktree from the verified fetched
   default-branch commit. Record the repository, remote, default branch, base
   commit, worktree path, task branch, creation result and verification
   evidence in the task's existing execution record. Verify with Git that the
   worktree is registered, its branch and HEAD match the recorded values, and
   it starts clean. Do all task edits and checks in that worktree.
5. If setup fails partway through, inspect Git's worktree and branch state
   before recovery. Remove only artifacts proven to have been created by this
   task, using a non-force operation and readback. Preserve ambiguous or
   pre-existing paths and refs.

The original checkout may already be dirty. That is not a reason to interrupt
or alter it: create the fresh task worktree beside it. Report any limitation
that prevents safe worktree creation rather than silently falling back to the
dirty checkout.

## Keep the review gate

Finishing local implementation, passing tests, opening a PR, or requesting
review does not authorize worktree cleanup. Keep the task worktree available
while the PR awaits owner review or merge. Do not merge a PR unless a separate,
current owner authorization covers that exact merge.

## Automatic cleanup after a verified merge

After the owner merges the PR, clean up automatically when all of these checks
pass:

The hosting client must run a post-merge callback or a bounded monitor for
unattended cleanup. Without such a mechanism, perform the check at the next
active Flow turn and report that unattended cleanup was not armed. A promise
in a skill file does not schedule a process.

1. Read the PR from its hosting service and verify its repository, number,
   source branch, target/default branch and merged state. Bind the PR's exact
   submitted head SHA and merge-result SHA from current readback.
2. Fetch/read back the target branch and verify the reported merge-result SHA
   is present in its history. Verify the task worktree still has the recorded
   source branch and its HEAD is the exact submitted head SHA. A mismatch,
   missing provider evidence, or a branch that has moved without an explained
   and verified relationship stops cleanup.
3. Verify the task/session registry and available host state show no active
   writer or process using this worktree. Verify the worktree has no staged,
   unstaged, conflicted, or untracked files and no unexpected user-created
   contents. Inspect status from the worktree itself; ignored build artifacts
   may remain only when their ownership is clear and they do not prevent a
   clean, non-force removal.
4. Run `git worktree remove <exact-task-worktree-path>` without `--force`. Never
   remove a path based only on its name, never force removal, never run broad
   `git worktree prune`, and do not delete branches or other worktrees as part
   of this cleanup.
5. Read back `git worktree list` and verify only that exact task worktree is
   gone. Record the merge proof, pre-removal branch/HEAD and clean-state proof,
   removal result and post-removal readback in the existing task record.

If any gate fails, preserve the worktree and its contents. State the specific
missing evidence or cleanup condition and the one action needed to resume.
Never describe local completion as merged or removed until the corresponding
readbacks prove it.

## Cleanup helper

Use [`scripts/cleanup_worktree.py`](../scripts/cleanup_worktree.py) from the
task's Git repository. It queries `gh` for the exact repository default branch
and PR, fetches that target branch, and checks the submitted head and merge
result against Git state. Its task JSON manifest must contain:

```json
{
  "schema_version": 1,
  "task_id": "<task-id>",
  "repository_path": "<original-repository-checkout>",
  "worktree_path": "<exact-task-worktree>",
  "remote": "origin",
  "repository": "<owner/repository>",
  "pr_number": 123,
  "branch": "<exact-source-branch>",
  "submitted_head_sha": "<full-40-character-sha>",
  "writer_readback": {
    "status": "IDLE",
    "active_writers": [],
    "worktree_path": "<exact-task-worktree>",
    "source": "<host session-registry readback reference>",
    "observed_at": "<timezone-aware timestamp no older than 60 seconds>"
  }
}
```

The host must build `writer_readback` from a current authoritative session/runtime
readback that covers every writer able to edit this worktree. The helper also
checks process current directories and open files with `lsof` when available.
If process inspection is unavailable, the host readback remains mandatory; if
that readback cannot be made or is stale, cleanup is blocked. A manifest is
evidence input, not proof that the host actually queried its registry.

Run without `--apply` first to verify and preview. The helper is read-only with
respect to the worktree in this mode, though it fetches the target branch into
a unique temporary Git ref (then removes that exact ref) and calls `gh`. Run it
from the project, replacing `<flow-skill-dir>` with this skill's directory:

```bash
python3 <flow-skill-dir>/scripts/cleanup_worktree.py --manifest <task-manifest.json>
```

Only the post-merge host callback or Flow lifecycle owner may pass `--apply`,
and only after a fresh writer readback. The helper then rechecks volatile gates,
uses non-force `git worktree remove`, and verifies the exact worktree disappeared:

```bash
python3 <flow-skill-dir>/scripts/cleanup_worktree.py --manifest <task-manifest.json> --apply
```

No callback/monitor is installed by this helper. A host must invoke it after
merge; otherwise Flow checks at the next active turn and reports that unattended
cleanup is not armed. It never merges, pushes, deletes a branch, or prunes other
worktrees.
