import subprocess
import sys
import os

WORKING_DIR = "turn_1/model_a"


def run_command(command):
    try:
        subprocess.run(command, check=True, text=True, cwd=WORKING_DIR)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while executing {command[0]}: {e}")
        sys.exit(1)


# Create virtual environment
run_command(["python", "-m", "venv", "venv"])

# Note: Activation of the virtual environment within the script is not straightforward
# Here we prepare the activation script path but actual activation would be outside this script
if sys.platform == "win32":
    activate_script = "venv\\Scripts\\activate"
else:
    activate_script = "venv/bin/activate"

# Verify virtual environment
command = ["which", "python"]
python_executable = subprocess.run(
    command,
    text=True,
    check=True,
    cwd=WORKING_DIR,
    stdout=subprocess.PIPE,
).stdout.strip()
print(f"Python executable: {python_executable}")

expected_python_executable = os.path.abspath(
    os.path.join(WORKING_DIR, "venv/bin/python")
)
print(f"Expected Python executable: {expected_python_executable}")

assert python_executable == expected_python_executable

# Install dependencies from requirements.txt
run_command(["pip", "install", "-r", "requirements.txt"])

# Run unit tests
run_command(["python", "-m", "unittest", "discover",
            "-s", "tests", "-p", "test_*.py"])
