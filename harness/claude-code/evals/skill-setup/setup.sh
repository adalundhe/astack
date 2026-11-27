#!/bin/bash
set -euo pipefail
mkdir -p program repo/src

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/app.py <<'EOF'
"""Application module (must not be edited during configuration setup)."""


def health() -> str:
    return "ok"
EOF

git -C repo add .
git -C repo commit -q -m "initial app"

cat > program/settings.json <<'EOF'
{
  "worker_minutes": 60,
  "wind_down_minutes": 5,
  "check_in_minutes": 5,
  "roles": {
    "lead": {"provider": "anthropic", "model": "opus", "effort": "high"},
    "worker": {"provider": "anthropic", "model": "sonnet", "effort": "medium"},
    "researcher": {"provider": "anthropic", "model": "haiku", "effort": "medium"},
    "reviewer": {"provider": "openai", "model": "gpt-5.4", "effort": "high"}
  }
}
EOF

cat > program/preferences.md <<'EOF'
# Approved Setup Preferences

Apply these exact choices to `program/settings.json` (do not modify `./repo` or external home directories):

- **Roles:** Keep `lead` (`anthropic`/`opus`/`high`), `worker` (`anthropic`/`sonnet`/`medium`), and `researcher` (`anthropic`/`haiku`/`medium`).
- **Approved reviewers:** Migrate the legacy reviewer entry (`openai`/`gpt-5.4`/`high`) out of `roles` and also include `anthropic`/`sonnet`/`high` (the team explicitly approves sending diffs to both OpenAI and Anthropic).
- **Timers:** `worker_minutes: 60`, `reviewer_minutes: 30`, `researcher_minutes: 30`, `wind_down_minutes: 5`, `check_in_minutes: 5`.
- **Autonomy:** `supervised` mode with empty `allow` list and the standard `deny` safeguards (`merge_pr`, `push_protected_branch`, `close_or_delete_others_pr`, `prod_deploy_or_destructive_migration`, `spend_money_or_billing_changes`, `publish_external_release`, `weaken_verification_gates`).
- **Automation:** Pure agentic (`agentic-only`, no Python venv needed).
EOF
