#!/usr/bin/env python3
import argparse
import configparser
import docker
import logging
import os
import shutil
import subprocess
import sys
import venv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: A namespace containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Automate Python application build and deployment process"
    )
    parser.add_argument(
        "--venv", default="venv",
        help="Name of the virtual environment (default: 'venv')"
    )
    parser.add_argument(
        "--requirements", default="requirements.txt",
        help="Path to the requirements file (default: 'requirements.txt')"
    )
    parser.add_argument(
        "--test-dir", default="tests",
        help="Directory containing test files (default: 'tests')"
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="Clean up the virtual environment after the build"
    )
    parser.add_argument(
        "--config", default="config.ini",
        help="Path to the configuration file (default: 'config.ini')"
    )
    parser.add_argument(
        "--dockerfile", default="Dockerfile",
        help="Path to the Dockerfile (default: 'Dockerfile')"
    )
    parser.add_argument(
        "--build-context", default=".",
        help="Path to the build context (default: current directory)"
    )
    return parser.parse_args()


def run_command(command, check=True, env=None):
    """
    Run a shell command safely, capturing and logging its output.

    Args:
        command (list): The command and arguments to run.
        check (bool): If True, raises a CalledProcessError if the command fails.
        env (dict, optional): Environment variables to pass to the command.

    Returns:
        subprocess.CompletedProcess: The result of the executed command.

    Raises:
        subprocess.CalledProcessError: If the command fails and `check` is True.
    """
    try:
        result = subprocess.run(
            command,
            env=env,
            text=True,
            check=check,
            capture_output=True,
        )
        logger.info(f"Command output (STDOUT): {result.stdout}")
        logger.info(f"Command output (STDERR): {result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.cmd}")
        logger.error(f"Error output: {e.stderr}")
        raise


def create_venv(venv_name):
    """
    Create a virtual environment.

    Args:
        venv_name (str): The name of the virtual environment to create.
    """
    logger.info(f"Creating virtual environment: {venv_name}")
    venv.create(venv_name, with_pip=True)


def get_venv_python(venv_name):
    """
    Get the path to the Python executable within the virtual environment.

    Args:
        venv_name (str): The name of the virtual environment.

    Returns:
        str: The path to the Python executable within the virtual environment.
    """
    if sys.platform == "win32":
        return os.path.join(venv_name, "Scripts", "python.exe")
    return os.path.join(venv_name, "bin", "python")


def install_dependencies(venv_python, requirements_file):
    """
    Install dependencies listed in the requirements file using pip.

    Args:
        venv_python (str): Path to the Python executable in the virtual environment.
        requirements_file (str): Path to the requirements file.

    Logs a warning if the requirements file does not exist.
    """
    if os.path.exists(requirements_file):
        logger.info(f"Installing dependencies from {requirements_file}")
        run_command([
            venv_python, "-m", "pip", "install", "-r", requirements_file
        ])
    else:
        logger.warning(
            f"Requirements file {requirements_file} not found. "
            "Skipping dependency installation."
        )


def run_tests(venv_python, test_dir):
    """
    Run unit tests using the unittest framework.

    Args:
        venv_python (str): Path to the Python executable in the virtual environment.
        test_dir (str): Directory containing the test files.
    """
    logger.info("Running unit tests")
    run_command([venv_python, "-m", "unittest", test_dir])


def cleanup(venv_name):
    """
    Remove the virtual environment directory.

    Args:
        venv_name (str): The name of the virtual environment to remove.
    """
    logger.info(f"Cleaning up virtual environment: {venv_name}")
    shutil.rmtree(venv_name, ignore_errors=True)


def load_config(config_file):
    """
    Load configuration from a file.

    Args:
        config_file (str): Path to the configuration file.

    Returns:
        configparser.ConfigParser: Parsed configuration.
    """
    logger.info(f"Loading configuration from {config_file}")
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def build_docker_image(image_name, dockerfile_path, build_context):
    """
    Build a Docker image.

    Args:
        image_name (str): Name for the Docker image.
        dockerfile_path (str): Path to the Dockerfile.
        build_context (str): Path to the build context.

    Returns:
        docker.models.images.Image: Built Docker image.
    """
    logger.info(f"Building Docker image: {image_name}")
    client = docker.from_env()
    image, build_logs = client.images.build(
        path=build_context,
        dockerfile=dockerfile_path,
        tag=image_name,
        rm=True
    )
    for log in build_logs:
        if 'stream' in log:
            logger.info(log['stream'].strip())
    return image


def tag_docker_image(image, repository, tag):
    """
    Tag a Docker image.

    Args:
        image (docker.models.images.Image): Docker image to tag.
        repository (str): Repository name.
        tag (str): Tag for the image.
    """
    logger.info(f"Tagging Docker image: {repository}:{tag}")
    image.tag(repository, tag)


def push_docker_image(repository, tag, username, password):
    """
    Push a Docker image to a registry.

    Args:
        repository (str): Repository name.
        tag (str): Tag of the image to push.
        username (str): Docker registry username.
        password (str): Docker registry password.
    """
    logger.info(f"Pushing Docker image: {repository}:{tag}")
    client = docker.from_env()
    # client.login(username=username, password=password)
    for line in client.images.push(repository, tag, stream=True, decode=True):
        logger.info(line)


def main():
    """
    Main function to orchestrate the build and deployment process.

    This function performs the following steps:
    1. Parses command-line arguments.
    2. Loads configuration from file.
    3. Creates a virtual environment.
    4. Installs dependencies.
    5. Runs unit tests.
    6. Builds a Docker image.
    7. Tags the Docker image.
    8. Pushes the Docker image to a registry.
    9. Cleans up the virtual environment if specified.

    If any step fails, it logs the error and exits with a non-zero status.
    """
    args = parse_arguments()
    config = load_config(args.config)

    try:
        create_venv(args.venv)
        venv_python = get_venv_python(args.venv)
        install_dependencies(venv_python, args.requirements)
        run_tests(venv_python, args.test_dir)

        # Docker operations
        image_name = config['Docker']['ImageName']
        repository = config['Docker']['Repository']
        tag = config['Docker']['Tag']
        username = config['Docker']['Username']
        password = config['Docker']['Password']

        image = build_docker_image(
            image_name, args.dockerfile, args.build_context)
        tag_docker_image(image, repository, tag)
        push_docker_image(repository, tag, username, password)

        logger.info("Build and deployment process completed successfully!")
    except Exception as e:
        logger.error(f"Build and deployment process failed: {str(e)}")
        sys.exit(1)
    finally:
        if args.cleanup:
            cleanup(args.venv)


if __name__ == "__main__":
    main()
