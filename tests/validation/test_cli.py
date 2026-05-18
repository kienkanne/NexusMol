import subprocess
import sys

def test_validate_run_vina_help():
    result = subprocess.run([sys.executable, "-m", "compdd.validation.cli", "run_vina", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--config" in result.stdout

def test_validate_run_dock6_help():
    result = subprocess.run([sys.executable, "-m", "compdd.validation.cli", "run_dock6", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--config" in result.stdout
