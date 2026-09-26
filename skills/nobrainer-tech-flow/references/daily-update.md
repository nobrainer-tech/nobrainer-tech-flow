# Daily release check and safe upgrade

Use `scripts/check_flow_update.py --client CLIENT` on the first active Flow
use of each local calendar day. The script caches the result per client,
day and installed version. Read the actual installed manifest or native
plugin identity first; a source checkout is not proof of the loaded version.
If the identity is unavailable, report `UNVERIFIED` and do not infer that
the client is current. A failed network check is `CHECK_FAILED`, not
`CURRENT`.

When `UPDATE_AVAILABLE`, tell the user the installed and latest version
and the verified release link. Upgrade only within the owner's recorded
standing authorization or after approval of the exact reviewed change.
Before applying, obtain the new release source at a verified immutable ref,
compare installation targets, run `validate_skills.py --suite`, then dry-run
`install_skills.py` and `install_personalization.py`. Preserve foreign
targets and dirty instructions. Apply the scoped update and read back
the installed source, selected MAIN model/effort, personal rules and a
clean-session Flow invocation. Source install, client loading and runtime
behavior are separate proof levels. If a migration needs a target overwrite,
credential or restart that is not authorized, stop at that exact gate.

For an inactive client, a scheduler may run the checker with `--unattended`
only when the client supports scheduling and its owner configures it.
The checker sends no notification by itself. Without a scheduler, the
contract is a check on the first use of that day, not an unattended
guarantee. Do not build a polling loop or duplicate automations.
