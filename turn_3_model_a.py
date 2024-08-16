#!/usr/bin/env python3
import configparser
import docker
import logging
import os
import requests
import sys
import venv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG_FILE = os.environ.get('CONFIG_FILE', 'config.ini')
VENV_NAME = os.environ.get('VENV_NAME', 'venv')
REQUIREMENTS_FILE = os.environ.get('REQUIREMENTS_FILE', 'requirements.txt')
TEST_DIR = os.environ.get('TEST_DIR', 'tests')
DOCKERFILE = os.environ.get('DOCKERFILE', 'Dockerfile')
BUILD_CONTEXT = os.environ.get('BUILD_CONTEXT', '.')

# Docker configuration
DOCKER_USERNAME = os.environ.get('DOCKER_USERNAME')
DOCKER_PASSWORD = os.environ.get('DOCKER_PASSWORD')

# Slack configuration for notifications
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')


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

    Raises:
        FileNotFoundError: If the requirements file does not exist.
    """
    if os.path.exists(requirements_file):
        logger.info(f"Installing dependencies from {requirements_file}")
        os.system(f"{venv_python} -m pip install -r {requirements_file}")
    else:
        raise FileNotFoundError(
            f"Requirements file {requirements_file} not found.")


def run_tests(venv_python, test_dir):
    """
    Run unit tests using the unittest framework.

    Args:
        venv_python (str): Path to the Python executable in the virtual environment.
        test_dir (str): Directory containing the test files.

    Raises:
        subprocess.CalledProcessError: If the tests fail.
    """
    logger.info("Running unit tests")
    result = os.system(f"{venv_python} -m unittest discover {test_dir}")
    if result != 0:
        raise subprocess.CalledProcessError(
            result, f"{venv_python} -m unittest discover {test_dir}")


def build_docker_image(image_name, dockerfile_path, build_context):
    """
    Build a Docker image.

    Args:
        image_name (str): Name for the Docker image.
        dockerfile_path (str): Path to the Dockerfile.
        build_context (str): Path to the build context.

    Returns:
        docker.models.images.Image: Built Docker image.

    Raises:
        docker.errors.BuildError: If the Docker build fails.
    """
    logger.info(f"Building Docker image: {image_name}")
    client = docker.from_env()
    try:
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
    except docker.errors.BuildError as e:
        logger.error(f"Docker build failed: {str(e)}")
        raise


def tag_docker_image(image, repository, tag):
    """
    Tag a Docker image.

    Args:
        image (docker.models.images.Image): Docker image to tag.
        repository (str): Repository name.
        tag (str): Tag for the image.

    Raises:
        docker.errors.APIError: If tagging the image fails.
    """
    logger.info(f"Tagging Docker image: {repository}:{tag}")
    try:
        image.tag(repository, tag)
    except docker.errors.APIError as e:
        logger.error(f"Failed to tag Docker image: {str(e)}")
        raise


def push_docker_image(repository, tag, username, password):
    """
    Push a Docker image to a registry.

    Args:
        repository (str): Repository name.
        tag (str): Tag of the image to push.
        username (str): Docker registry username.
        password (str): Docker registry password.

    Raises:
        docker.errors.APIError: If pushing the image fails.
    """
    logger.info(f"Pushing Docker image: {repository}:{tag}")
    client = docker.from_env()
    try:
        client.login(username=username, password=password)
        for line in client.images.push(repository, tag, stream=True, decode=True):
            logger.info(line)
    except docker.errors.APIError as e:
        logger.error(f"Failed to push Docker image: {str(e)}")
        raise


def send_slack_notification(message):
    """
    Send a notification to Slack.

    Args:
        message (str): The message to send.

    Raises:
        requests.RequestException: If sending the Slack message fails.
    """
    if SLACK_WEBHOOK_URL:
        try:
            response = requests.post(SLACK_WEBHOOK_URL, json={"text": message})
            response.raise_for_status()
            logger.info("Slack notification sent successfully")
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
    else:
        logger.warning(
            "Slack webhook URL not configured. Skipping notification.")


def rollback_deployment(repository, previous_tag):
    """
    Rollback to the previous deployment.

    Args:
        repository (str): Repository name.
        previous_tag (str): Tag of the previous deployment.

    Raises:
        Exception: If rollback fails.
    """
    logger.info(
        f"Rolling back to previous deployment: {repository}:{previous_tag}")
    try:
        # Implement your rollback logic here
        # This could involve redeploying the previous version or updating Kubernetes
        pass
    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        raise


def main():
    """
    Main function to orchestrate the build and deployment process.
    """
    config = load_config(CONFIG_FILE)
    previous_tag = config['Docker']['Tag']

    try:
        create_venv(VENV_NAME)
        venv_python = get_venv_python(VENV_NAME)
        install_dependencies(venv_python, REQUIREMENTS_FILE)
        run_tests(venv_python, TEST_DIR)

        # Docker operations
        image_name = config['Docker']['ImageName']
        repository = config['Docker']['Repository']
        new_tag = f"v{config['Docker']['Version']}"

        image = build_docker_image(image_name, DOCKERFILE, BUILD_CONTEXT)
        tag_docker_image(image, repository, new_tag)
        push_docker_image(repository, new_tag,
                          DOCKER_USERNAME, DOCKER_PASSWORD)

        # Update config with new version
        config['Docker']['Tag'] = new_tag
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

        logger.info("Build and deployment process completed successfully!")
        send_slack_notification("Deployment successful! 🎉")

    except Exception as e:
        logger.error(f"Build and deployment process failed: {str(e)}")
        send_slack_notification(f"Deployment failed: {str(e)} ❌")
        try:
            rollback_deployment(repository, previous_tag)
            send_slack_notification(
                f"Rolled back to previous version: {previous_tag}")
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {str(rollback_error)}")
            send_slack_notification(
                f"Rollback failed: {str(rollback_error)} ❌❌")
        sys.exit(1)


if __name__ == "__main__":
    main()
