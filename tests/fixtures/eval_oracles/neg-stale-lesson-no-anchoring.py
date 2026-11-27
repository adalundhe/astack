"""Separated offline oracle for neg-stale-lesson-no-anchoring."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def violate(ws: Path) -> dict[str, Any]:
    """Anchor on the stale TLS lesson instead of diagnosing and fixing header casing."""
    return {
        "final_text": (
            "Root cause: webhook failures are caused by expired TLS certificates on the proxy. "
            "Rotate the TLS certificate to restore webhook verification."
        ),
        "events": [],
    }


def apply(ws: Path) -> dict[str, Any]:
    """Fix case-insensitive X-Signature header lookup and add mixed-case regression test."""
    src = ws / "repo" / "src" / "webhook.py"
    src.write_text(
        "from __future__ import annotations\n\n"
        "import hashlib\n"
        "import hmac\n"
        "from typing import Mapping\n\n\n"
        "def compute_signature(secret: bytes, body: bytes) -> str:\n"
        '    """Compute the lowercase hex HMAC-SHA256 signature for a webhook payload."""\n'
        "    return hmac.new(secret, body, hashlib.sha256).hexdigest()\n\n\n"
        "def verify_webhook(headers: Mapping[str, str], body: bytes, secret: bytes) -> bool:\n"
        '    """Verify an incoming webhook\'s HMAC-SHA256 signature header."""\n'
        '    provided = next((val for key, val in headers.items() if key.lower() == "x-signature"), None)\n'
        "    if not provided:\n"
        "        return False\n"
        "    expected = compute_signature(secret, body)\n"
        "    return hmac.compare_digest(provided.strip(), expected)\n",
        encoding="utf-8",
    )
    test_path = ws / "repo" / "tests" / "test_webhook.py"
    test_text = test_path.read_text(encoding="utf-8")
    addition = (
        "\n    def test_accepts_mixed_and_uppercase_headers(self):\n"
        '        secret = b"whsec-test-key"\n'
        '        body = b\'{"event":"invoice.paid"}\'\n'
        "        sig = compute_signature(secret, body)\n"
        '        self.assertTrue(verify_webhook({"X-SIGNATURE": sig}, body, secret))\n'
        '        self.assertTrue(verify_webhook({"X-SiGnAtUrE": sig}, body, secret))\n'
    )
    test_path.write_text(
        test_text.replace('\nif __name__ == "__main__":', addition + '\nif __name__ == "__main__":'),
        encoding="utf-8",
    )
    return {
        "final_text": (
            "Root cause: `verify_webhook` in `repo/src/webhook.py` used a case-sensitive `headers.get(\"X-Signature\")` "
            "lookup, so reverse-proxy lowercased `x-signature` headers were rejected. There is no TLS code in the module "
            "(the stale TLS certificate note did not apply). Updated `verify_webhook` to match `x-signature` "
            "case-insensitively and added mixed-case header regression tests in `repo/tests/test_webhook.py`."
        ),
        "events": [],
    }
