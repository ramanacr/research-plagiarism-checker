import sys
import subprocess
import unittest

class TestAPIIsolation(unittest.TestCase):
    def test_api_isolation_imports(self):
        # Run import check in a clean, isolated Python subprocess
        code = (
            "import sys\n"
            "import src.api\n"
            "assert 'src.attention.resolver' not in sys.modules, 'resolver was loaded'\n"
            "assert 'src.attention.worker' not in sys.modules, 'worker was loaded'\n"
            "assert 'src.attention.connectors.wikimedia' not in sys.modules, 'wikimedia was loaded'\n"
            "print('SUCCESS')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"APIIsolation failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

if __name__ == "__main__":
    unittest.main()
