#!/usr/bin/env python3
import os
import subprocess
import venv
import sys


WORKING_DIR = "turn_1/model_b"


def create_virtual_environment():
    """
    Create a virtual environment named 'venv' in the current directory.
    """
    print("Creating virtual environment...")
    venv.create(os.path.join(WORKING_DIR, "venv"), with_pip=True)
    print("Virtual environment created successfully.")


def activate_virtual_environment():
    """
    Activate the virtual environment.
    """
    print("Activating virtual environment...")
    if sys.platform == "win32":
        activate_script = os.path.join("venv", "Scripts", "activate")
    else:
        activate_script = os.path.join("venv", "bin", "activate")

    activate_command = f"source {activate_script}"
    subprocess.run(activate_command, shell=True, check=True, cwd=WORKING_DIR)
    print("Virtual environment activated successfully.")


def install_dependencies():
    """
    Install dependencies from requirements.txt file.
    """
    print("Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install",
                   "-r", "requirements.txt"], check=True, cwd=WORKING_DIR)
    print("Dependencies installed successfully.")


def run_unit_tests():
    """
    Run unit tests using unittest.
    """
    print("Running unit tests...")
    subprocess.run([sys.executable, "-m", "unittest",
                   "discover", "-v", "-s", "tests"], check=True, cwd=WORKING_DIR)
    print("Unit tests completed successfully.")


def verify_virtual_environment():
    """
    Verify that the virtual environment has been created and activated successfully.
    """
    print("Verifying virtual environment...")
    # Verify that the virtual environment is activated
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

    print("Virtual environment verified successfully.")


def main():
    try:
        create_virtual_environment()
        activate_virtual_environment()
        verify_virtual_environment()
        install_dependencies()
        run_unit_tests()
        print("Build process completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred during the build process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
