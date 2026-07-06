from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class OkfContractTest(unittest.TestCase):
    def test_repo_okf_contract_is_valid(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_okf.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
