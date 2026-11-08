# Next release

I added guided setup for the extender and refreshed the operator documentation.

- Extender setup checks whether TCP 443 is occupied, whether the provider binary can bind it, and what host firewall rules are missing. It prints exact commands and asks before applying changes. `--yes` or `--force` is the only non-interactive approval.
- FreeBSD extender setup is print-only and untested this release. It prints the `sysctl` commands and undo instructions without making changes. Regular providing on FreeBSD is unaffected.
- UDP 53 is optional and user-managed. Setup does not inspect or open it.
- Firewalld runtime and permanent rules are planned separately. Setup does not reload firewalld. Adding the bind capability preserves existing file capabilities.
- The Docker log follower and the hot-swap candidate bind race remain known limitations. This release does not fix them.
