#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenChecker Agent Module

This module provides the main agent functionality for processing project check tasks
from message queues. It handles downloading project sources, executing various checkers,
and sending results back via callbacks.

Author: OpenChecker Team
"""

# Standard library imports
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List

# Local imports
from checkers.bestpractices_checker import bestpractices_checker
from checkers.binary_checker import binary_checker
from checkers.changed_files_checker import changed_files_detector
from checkers.dangerous_workflow_checker import dangerous_workflow_checker
from checkers.document_checker import (
    api_doc_checker,
    build_doc_checker,
    readme_opensource_checker
)
from checkers.fuzzing_checker import fuzzing_checker
from checkers.dependency_update_tool_checker import dependency_update_tool_checker
from checkers.packaging_checker import packaging_checker
from checkers.pinned_dependencies_checker import pinned_dependencies_checker
from checkers.release_checker import release_checker
from checkers.sast_checker import sast_checker
from checkers.security_policy_checker import security_policy_checker
from checkers.sonar_checker import sonar_checker
from checkers.standard_command_checker import (
    code_count_checker,
    criticality_score_checker,
    ohpm_info_checker,
    package_info_checker,
    scorecard_score_checker,
    repo_country_organizations_checker,
    eol_checker
)
from checkers.token_permissions_checker import token_permissions_checker
from checkers.url_checker import url_checker
from checkers.webhooks_checker import webhooks_checker
from common import shell_exec
from constans import shell_script_handlers
from exponential_backoff import post_with_backoff
from helper import read_config
from logger import get_logger, log_performance, setup_logging
from message_queue import consumer
from platform_adapter import platform_manager

# Setup logging
setup_logging(
    log_level=os.getenv('LOG_LEVEL', 'INFO'),
    log_format=os.getenv('LOG_FORMAT', 'structured'),
    enable_console=True,
    enable_file=False,
    log_dir='logs'
)

# Get logger for agent module
logger = get_logger('openchecker.agent')

# Configuration setup
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(file_dir)
config_file = os.path.join(project_root, "config", "config.ini")
config = read_config(config_file)

def env_set():
    """
    设置环境变量，通过读取config.ini文件对环境变量进行统一管理

    其他位置（例如k8s 中configmap和container.env ）设置的同名变量值会在这里被覆盖
    """
    github_token = config["Github"].get("access_key", "")
    gitee_token = config["Gitee"].get("access_key", "")
    gitcode_token = config["GitCode"].get("access_key", "")
    #作用于scocard_score、critiaclity_score、github_api checker
    os.environ['GITHUB_AUTH_TOKEN'] = github_token
    #作用于gitee_api checker
    os.environ['GITEE_AUTH_TOKEN'] = gitee_token
    #作用于gitcode_api checker
    os.environ['GITCODE_AUTH_TOKEN'] = gitcode_token

    logger.info(f"已从配置文件config.ini设置环境变量")

env_set()

def get_licenses_name(data: Dict[str, Any]) -> str:
    """
    Extract license name from license data.
    
    Args:
        data: License data dictionary
        
    Returns:
        License name or None if not found
    """
    return next(
        (license['meta']['title'] 
         for license in data.get('licenses', []) 
         if license.get('meta', {}).get('title')), 
        None
    )


def ruby_licenses(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Ruby licenses by detecting missing licenses from GitHub repositories.
    
    Args:
        data: Dependency checker output data
        
    Returns:
        Updated data with detected licenses
    """
    github_url_pattern = "https://github.com/"
    
    for item in data["analyzer"]["result"]["packages"]:
        declared_licenses = item["declared_licenses"]
        homepage_url = item.get('homepage_url', '')
        vcs_url = item.get('vcs_processed', {}).get('url', '').replace('.git', '')

        # Check if declared_licenses is empty
        if not declared_licenses or len(declared_licenses) == 0:
            # Prioritize checking if vcs_url is a GitHub address
            if vcs_url.startswith(github_url_pattern):
                project_url = vcs_url
            elif homepage_url.startswith(github_url_pattern):
                project_url = homepage_url
            else:
                project_url = None
                
            # If a valid GitHub address is found, clone the repository and call licensee
            if project_url:
                shell_script = shell_script_handlers["license-detector"].format(project_url=project_url)
                result, error = shell_exec(shell_script)
                
                if error is None:
                    try:
                        license_info = json.loads(result)
                        licenses_name = get_licenses_name(license_info)
                        item['declared_licenses'].append(licenses_name)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from {project_url}: {e}")
                else:
                    logger.error(f"ruby_licenses job failed: {project_url}, error: {error}")
    
    return data


def dependency_checker_output_process(output: bytes) -> Dict[str, Any]:
    """
    Process dependency checker output and categorize packages by license status.
    
    Args:
        output: Raw output from dependency checker
        
    Returns:
        Processed result with categorized packages
    """
    if not bool(output):
        return {}

    result = json.loads(output.decode('utf-8'))
    result = ruby_licenses(result)
    
    try:
        packages = result["analyzer"]["result"]["packages"]
        result = {
            "packages_all": [],
            "packages_with_license_detect": [],
            "packages_without_license_detect": []
        }

        for package in packages:
            result["packages_all"].append(package["purl"])
            license = package["declared_licenses"]
            if license is not None and len(license) > 0:
                result["packages_with_license_detect"].append(package["purl"])
            else:
                result["packages_without_license_detect"].append(package["purl"])

    except Exception as e:
        logger.error(f"Error processing dependency-checker output: {e}")
        return {}

    return result


def request_url(url: str, payload: Dict[str, Any]) -> tuple[str, str]:
    """
    Send HTTP POST request with exponential backoff.
    
    Args:
        url: Target URL
        payload: Request payload
        
    Returns:
        Tuple of (response_text, error_message)
    """
    response = post_with_backoff(url=url, json=payload)

    if response.status_code == 200:
        return response.text, None
    else:
        return None, f"Failed to send request. Status code: {response.status_code}"


@log_performance('openchecker.agent')
def callback_func(ch, method, properties, body):
    """
    Message queue callback function, handles project check tasks.
    
    Args:
        ch: Message channel
        method: Message method
        properties: Message properties
        body: Message body
    """
    logger.info(
        "Starting to process message queue task",
        extra={
            'extra_fields': {
                'delivery_tag': method.delivery_tag,
                'timestamp': datetime.now().isoformat()
            }
        }
    )

    original_cwd = os.getcwd()
    
    try:
        message = json.loads(body.decode('utf-8'))
        command_list = message.get('command_list', [])
        project_url = message.get('project_url')
        commit_hash = message.get("commit_hash")
        access_token = message.get("access_token")
        callback_url = message.get('callback_url')
        task_metadata = message.get('task_metadata', {})
        version_number = task_metadata.get("version_number", "None")
        
        project_url = project_url.replace(".git", "")
        logger.info(
            f"Starting to process project: {project_url}",
            extra={
                'extra_fields': {
                    'project_url': project_url,
                    'command_count': len(command_list),
                    'commands': command_list,
                    'callback_url': callback_url,
                    'version_number': version_number
                }
            }
        )

        if not project_url:
            logger.error("Project URL is required")
            return

        repos_dir = config.get("OpenCheck", {}).get("repos_dir", "/tmp/repos")
        logger.info(f"Repository directory: {repos_dir}")

        if not os.path.exists(repos_dir):
            os.makedirs(repos_dir, exist_ok=True)
            logger.info(f"Created repository directory: {repos_dir}")

        os.chdir(repos_dir)
        logger.info(f"Switched to working directory: {os.getcwd()}")

        res_payload = {
            "command_list": command_list,
            "project_url": project_url,
            "task_metadata": task_metadata,
            "scan_results": {}
        }

        if not _download_project_source(project_url, version_number):
            _handle_error_and_nack(ch, method, body, "Failed to download project source")
            return

        _generate_lock_files(project_url)
        _execute_commands(command_list, project_url, res_payload, commit_hash, access_token)
        _cleanup_project_source(project_url)

        os.chdir(original_cwd)
        logger.info(f"Restored working directory: {os.getcwd()}")

        _send_results(callback_url, res_payload)
        ch.basic_ack(delivery_tag=method.delivery_tag)

        logger.info(
            f"Project {project_url} processed successfully",
            extra={
                'extra_fields': {
                    'project_url': project_url,
                    'command_count': len(command_list),
                    'timestamp': datetime.now().isoformat()
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error occurred while processing message: {e}", exc_info=True)

        try:
            os.chdir(original_cwd)
            logger.info(f"Restored working directory after exception: {os.getcwd()}")
        except:
            pass

        _handle_error_and_nack(ch, method, body, str(e))


def _download_project_source(project_url: str, version_number: str) -> bool:
    """
    Download project source code.
    
    Args:
        project_url: Project URL
        version_number: Version number
        
    Returns:
        Whether successful
    """
    try:
        shell_script = shell_script_handlers["download-checkout"].format(
            project_url=project_url, 
            version_number=version_number
        )
        result, error = shell_exec(shell_script)
        
        if error is None:
            logger.info(f"Source code download completed: {project_url}")
            return True
        else:
            logger.error(f"Source code download failed: {project_url}, error: {error}")
            return False
            
    except Exception as e:
        logger.error(f"Source code download exception: {e}")
        return False


def _generate_lock_files(project_url: str) -> None:
    """
    Generate lock files.
    
    Args:
        project_url: Project URL
    """
    try:
        shell_script = shell_script_handlers["generate-lock_files"].format(project_url=project_url)
        result, error = shell_exec(shell_script)
        
        if error is None:
            logger.info(f"Lock files generation completed: {project_url}")
        else:
            logger.error(f"Lock files generation failed: {project_url}, error: {error}")
            
    except Exception as e:
        logger.error(f"Lock files generation exception: {e}")


def _execute_commands(
    command_list: List[str],
    project_url: str,
    res_payload: Dict[str, Any],
    commit_hash: str,
    access_token: str
) -> None:
    """
    Execute command list.
    
    Args:
        command_list: Command list
        project_url: Project URL
        res_payload: Response payload
        commit_hash: Commit hash
        access_token: Access token
    """
    command_switch = {
        'binary-checker': lambda: binary_checker(project_url, res_payload),
        'release-checker': lambda: release_checker(project_url, res_payload),
        'url-checker': lambda: url_checker(project_url, res_payload),
        'sonar-scanner': lambda: sonar_checker(project_url, res_payload, config),
        'osv-scanner': lambda: _handle_shell_script_command('osv-scanner', project_url, res_payload),
        'scancode': lambda: _handle_shell_script_command('scancode', project_url, res_payload),
        'dependency-checker': lambda: _handle_shell_script_command('dependency-checker', project_url, res_payload),
        'readme-checker': lambda: _handle_shell_script_command('readme-checker', project_url, res_payload),
        'maintainers-checker': lambda: _handle_shell_script_command('maintainers-checker', project_url, res_payload),
        'languages-detector': lambda: _handle_shell_script_command('languages-detector', project_url, res_payload),
        'oat-scanner': lambda: _handle_shell_script_command('oat-scanner', project_url, res_payload),
        'license-detector': lambda: _handle_shell_script_command('license-detector', project_url, res_payload),
        'api-doc-checker': lambda: api_doc_checker(project_url, res_payload),
        'build-doc-checker': lambda: build_doc_checker(project_url, res_payload),
        'readme-opensource-checker': lambda: readme_opensource_checker(project_url, res_payload),
        'bestpractices-checker': lambda: bestpractices_checker(project_url, res_payload),
        'dangerous-workflow-checker': lambda: dangerous_workflow_checker(project_url, res_payload),
        'dependency-update-tool-checker': lambda: dependency_update_tool_checker(project_url, res_payload),
        'fuzzing-checker': lambda: fuzzing_checker(project_url, res_payload),
        'packaging-checker': lambda: packaging_checker(project_url, res_payload),
        'pinned-dependencies-checker': lambda: pinned_dependencies_checker(project_url, res_payload),
        'sast-checker': lambda: sast_checker(project_url, res_payload),
        'security-policy-checker': lambda: security_policy_checker(project_url, res_payload),
        'token-permissions-checker': lambda: token_permissions_checker(project_url, res_payload),
        'webhooks-checker': lambda: webhooks_checker(project_url, res_payload, access_token),
        'changed-files-since-commit-detector': lambda: changed_files_detector(project_url, res_payload, commit_hash),
        'criticality-score': lambda: criticality_score_checker(project_url, res_payload),
        'scorecard-score': lambda: scorecard_score_checker(project_url, res_payload),
        'code-count': lambda: code_count_checker(project_url, res_payload),
        'package-info': lambda: package_info_checker(project_url, res_payload),
        'ohpm-info': lambda: ohpm_info_checker(project_url, res_payload),
        'repo-country-organizations': lambda: repo_country_organizations_checker(project_url, res_payload),
        'eol-checker': lambda: eol_checker(project_url, res_payload)
    }
    
    for command in command_list:
        if command in command_switch:
            try:
                command_switch[command]()
            except Exception as e:
                logger.error(f"Error executing command {command}: {e}")
                res_payload["scan_results"][command] = {"error": str(e)}
        else:
            logger.warning(f"Unknown command: {command}")


def _handle_shell_script_command(
    command: str,
    project_url: str,
    res_payload: Dict[str, Any]
) -> None:
    """
    Generic function to handle shell script commands.
    
    Args:
        command: Command name
        project_url: Project URL
        res_payload: Response payload
    """
    try:
        if command not in shell_script_handlers:
            logger.error(f"No shell script handler found for command: {command}")
            return
        
        shell_script = shell_script_handlers[command].format(project_url=project_url)
        result, error = shell_exec(shell_script)
        
        if error is None:
            logger.info(f"{command} job done: {project_url}")
            
            processed_result = _process_command_result(command, result)
            res_payload["scan_results"][command] = processed_result
        else:
            logger.error(f"{command} job failed: {project_url}, error: {error}")
            res_payload["scan_results"][command] = {"error": error.decode("utf-8")}
            
    except Exception as e:
        logger.error(f"{command} job failed: {project_url}, error: {e}")
        res_payload["scan_results"][command] = {"error": str(e)}


def _process_command_result(command: str, result: bytes) -> Any:
    """
    Process results according to command type.
    
    Args:
        command: Command name
        result: Original result
        
    Returns:
        Processed result
    """
    if not result:
        return {}
    
    result_str = result.decode('utf-8')
    
    json_commands = ['osv-scanner', 'scancode', 'languages-detector']
    if command in json_commands:
        try:
            return json.loads(result_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON for {command}: {e}")
            return {"raw_output": result_str}
    
    if command == 'dependency-checker':
        return dependency_checker_output_process(result)
    elif command == 'oat-scanner':
        return parse_oat_txt_to_json(result_str)
    
    return result_str


def _cleanup_project_source(project_url: str) -> None:
    """
    Clean up project source code.
    
    Args:
        project_url: Project URL
    """
    try:
        shell_script = shell_script_handlers["remove-source-code"].format(project_url=project_url)
        result, error = shell_exec(shell_script)
        
        if error is None:
            logger.info(f"Source code cleanup done: {project_url}")
        else:
            logger.warning(f"Source code cleanup failed: {project_url}, error: {error}")
            
    except Exception as e:
        logger.error(f"Exception during source cleanup: {e}")


def _send_results(callback_url: str, res_payload: Dict[str, Any]) -> None:
    """
    Send results to callback URL.
    
    Args:
        callback_url: Callback URL
        res_payload: Response payload
    """
    if callback_url:
        try:
            response, err = request_url(callback_url, res_payload)
            if err is None:
                logger.info("Results sent successfully")
            else:
                logger.error(f"Failed to send results: {err}")
        except Exception as e:
            logger.error(f"Exception sending results: {e}")


def _handle_error_and_nack(ch, method, body, error_msg: str) -> None:
    """
    Handle error and nack message.
    
    Args:
        ch: Message channel
        method: Message method
        body: Message body
        error_msg: Error message
    """
    logger.error(f"Putting message to dead letters: {error_msg}")
    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def parse_oat_txt_to_json(txt: str) -> Dict[str, Any]:
    """
    Parse OAT tool output text report to JSON format.
    
    Args:
        txt: OAT tool output text content
        
    Returns:
        Parsed JSON format data
    """
    try:
        de_str = txt.decode('unicode_escape') if isinstance(txt, bytes) else txt
        result = {}
        lines = de_str.splitlines()
        current_section = None
        pattern = r"Name:\s*(.+?)\s*Content:\s*(.+?)\s*Line:\s*(\d+)\s*Project:\s*(.+?)\s*File:\s*(.+)"

        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            total_count_match = re.search(r"^(.*) Total Count:\s*(\d+)", line, re.MULTILINE)
            category_name = total_count_match.group(1).strip() if total_count_match else "Unknown"

            if 'Total Count' in line:
                current_section = category_name
                total_count = int(line.split(":")[1].strip())
                result[current_section] = {"total_count": total_count, "details": []}
            elif line.startswith("Name:"):
                matches = re.finditer(pattern, line)
                for match in matches:
                    entry = {
                        "name": match.group(1).strip(),
                        "content": match.group(2).strip(),
                        "line": int(match.group(3).strip()),
                        "project": match.group(4).strip(),
                        "file": match.group(5).strip(),
                    }
                if current_section and "details" in result[current_section]:
                    result[current_section]["details"].append(entry)
        return result
    except Exception as e:
        logger.error(f"parse_oat_txt error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    consumer(config["RabbitMQ"], "opencheck", callback_func)
    logger.info('Agents server ended.')

# TODO: Add an adapter for various code platforms, like github, gitee, gitcode, etc.