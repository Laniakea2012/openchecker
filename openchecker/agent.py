import subprocess
from message_queue import consumer
from helper import read_config
from datetime import datetime
from exponential_backoff import post_with_backoff, completion_with_backoff
import json
import requests
import re
import time
import os
from ghapi.all import GhApi
import zipfile
import io
import logging
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s : %(message)s')

# Load configuration
config = read_config('config/config.ini')

def get_licenses_name(data: Dict) -> Optional[str]:
    """
    Extract license name from license data
    
    Args:
        data: Dictionary containing license information
        
    Returns:
        License name if found, None otherwise
    """
    return next(
        (license['meta']['title'] 
         for license in data.get('licenses', []) 
         if license.get('meta', {}).get('title')), 
        None
    )

def ruby_licenses(data: Dict) -> Dict:
    """
    Process Ruby package licenses using licensee tool
    
    Args:
        data: Dictionary containing package information
        
    Returns:
        Updated data with license information
    """
    github_url_pattern = "https://github.com/"
    for item in data["analyzer"]["result"]["packages"]:
        declared_licenses = item["declared_licenses"]
        homepage_url = item.get('homepage_url', '')
        vcs_url = item.get('vcs_processed', {}).get('url', '').replace('.git', '')

        # Check if declared_licenses is empty
        if not declared_licenses or len(declared_licenses)==0:
            # Prioritize vcs_url if it's a GitHub URL
            if vcs_url.startswith(github_url_pattern):
                project_url = vcs_url
            elif homepage_url.startswith(github_url_pattern):
                project_url = homepage_url
            else:
                project_url = None
                
            # If valid GitHub URL found, clone repo and run licensee
            if project_url:
                shell_script=f"""
                    project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                    if [ ! -e "$project_name" ]; then
                        GIT_ASKPASS=/bin/true git clone --depth=1 {project_url} > /dev/null
                    fi
                    licensee detect "$project_name" --json
                    rm -rf $project_name > /dev/null
                """
                result, error = shell_exec(shell_script)
                if error is None:
                    try:
                        license_info = json.loads(result)
                        licenses_name = get_licenses_name(license_info)
                        item['declared_licenses'].append(licenses_name)
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse JSON from {project_url}: {e}")
                else:
                    logging.error(f"ruby_licenses job failed: {project_url}, error: {error}")
    return data

def dependency_checker_output_process(output: bytes) -> Dict:
    """
    Process dependency checker output
    
    Args:
        output: Raw output from dependency checker
        
    Returns:
        Processed dependency information
    """
    if not bool(output):
        return {}

    try:
    result = json.loads(output.decode('utf-8'))
    result = ruby_licenses(result)
        packages = result["analyzer"]["result"]["packages"]
        processed_result = {
            "packages_all": [],
            "packages_with_license_detect": [],
            "packages_without_license_detect": []
        }

        for package in packages:
            processed_result["packages_all"].append(package["purl"])
            license = package["declared_licenses"]
            if license and len(license) > 0:
                processed_result["packages_with_license_detect"].append(package["purl"])
            else:
                processed_result["packages_without_license_detect"].append(package["purl"])

    except Exception as e:
        logging.error(f"Error processing dependency-checker output: {e}")
        return {}

    return processed_result

def shell_exec(shell_script: str, param: Optional[str] = None) -> Tuple[Optional[bytes], Optional[bytes]]:
    """
    Execute shell command with error handling
    
    Args:
        shell_script: Shell script to execute
        param: Optional parameter to append to script
        
    Returns:
        Tuple of (output, error)
    """
    try:
        if param is not None:
            process = subprocess.Popen(
                ["/bin/bash", "-c", shell_script + " " + param],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )
    else:
            process = subprocess.Popen(
                [shell_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
    shell_output, error = process.communicate()

    if process.returncode == 0:
        return shell_output, None
    else:
        return None, error
    except Exception as e:
        logging.error(f"Shell execution failed: {e}")
        return None, str(e).encode()

def request_url(url: str, payload: Dict) -> Optional[str]:
    """
    Send POST request with retry mechanism
    
    Args:
        url: Target URL
        payload: Request payload
        
    Returns:
        Response text if successful, None otherwise
    """
    response = post_with_backoff(url=url, json=payload)

    if response.status_code == 200:
        logging.info("Request sent successfully.")
        return response.text
    else:
        logging.error(f"Failed to send request. Status code: {response.status_code}")
        return None

def check_readme_opensource(project_url: str) -> Tuple[bool, Optional[str]]:
    """
    Check if project has a properly formatted README.OpenSource file
    
    Args:
        project_url: URL of the project repository
        
    Returns:
        Tuple of (success, error_message)
    """
    project_name = os.path.basename(project_url).replace('.git', '')

    if not os.path.exists(project_name):
        subprocess.run(["git", "clone", project_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    readme_file = os.path.join(project_name, "README.OpenSource")
    if os.path.isfile(readme_file):
        with open(readme_file, 'r', encoding='utf-8') as file:
            try:
                content = json.load(file)

                if isinstance(content, list):
                    required_keys = [
                        "Name", "License", "License File",
                        "Version Number", "Owner", "Upstream URL", "Description"
                    ]

                    all_entries_valid = True
                    for entry in content:
                        if not isinstance(entry, dict) or not all(key in entry for key in required_keys):
                            all_entries_valid = False
                            break

                    if all_entries_valid:
                        return True, None
                    else:
                        return False, "The README.OpenSource file exists but is not properly formatted."

            except json.JSONDecodeError:
                return False, "README.OpenSource is not properly formatted."
    else:
        return False, "README.OpenSource does not exist."

def check_doc_content(project_url: str, doc_type: str) -> Tuple[List[str], Optional[str]]:
    """
    Check project documentation content
    
    Args:
        project_url: URL of the project repository
        doc_type: Type of documentation to check ('build-doc' or 'api-doc')
        
    Returns:
        Tuple of (document_files, error_message)
    """
    project_name = os.path.basename(project_url).replace('.git', '')

    if not os.path.exists(project_name):
        subprocess.run(["git", "clone", project_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    dir_list = [project_name, project_name + '/' + 'doc', project_name + '/' + 'docs']

    def get_documents_in_directory(path: str) -> List[str]:
        """
        Get all markdown documents in a directory
        
        Args:
            path: Directory path to search
            
        Returns:
            List of markdown document paths
        """
        documents = []
        if not os.path.exists(path):
            return documents
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            if os.path.isfile(full_path) and item.endswith(('.md', '.markdown')):
                documents.append(full_path)
        return documents

    documents = []
    for dir in dir_list:
        documents.extend(get_documents_in_directory(dir))

    if doc_type == "build-doc":
        do_link_include_check = True
        templates = """
            You are a professional programmer, please assess whether the provided text offers a thorough and in-depth introduction to the processes of software compilation and packaging.
            If the text segment introduce the software compilation and packaging completely, please return 'YES'; otherwise, return 'NO'.
            You need to ensure the accuracy of your answers as much as possible, and if unsure, please simply answer NO. Your response must not include other content.

            Text content as below:

            {text}

        """
    elif doc_type == "api-doc":
        do_link_include_check = False
        templates = """
            You are a professional programmer, please assess whether the provided text offer a comprehensive introduction to the use of software API.
            If the text segment introduce the software API completely, please return 'YES'; otherwise, return 'NO'.
            You need to ensure the accuracy of your answers as much as possible, and if unsure, please simply answer NO. Your response must not include other content.

            Text content as below:

            {text}

        """
    else:
        logging.info(f"Unsupported documentation type: {doc_type}")
        return [], None

    build_doc_file = []
    for document in documents:
        with open(document, 'r') as file:
            markdown_text = file.read()
            chunk_size = 3000
            chunks = [markdown_text[i:i+chunk_size] for i in range(0, len(markdown_text), chunk_size)]

        for _, chunk in enumerate(chunks):
            messages = [
                {
                    "role": "user",
                    "content": templates.format(text=chunk)
                }
            ]

            external_build_doc_link = "https://gitee.com/openharmony-tpc/docs/blob/master/OpenHarmony_har_usage.md"
            if do_link_include_check and external_build_doc_link.lower() in chunk.lower():
                return build_doc_file, None

            result = completion_with_backoff(messages=messages, temperature=0.2)
            if result == "YES":
                build_doc_file.append(document)
                return build_doc_file, None
    return build_doc_file, None

def check_release_content(project_url: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Check project release content including signatures and release notes
    
    Args:
        project_url: URL of the project repository
        
    Returns:
        Tuple of (release_info, error_message)
    """
    owner_name = re.match(r"https://(?:github|gitee|gitcode).com/([^/]+)/", project_url).group(1)
    repo_name = re.sub(r'\.git$', '', os.path.basename(project_url))

    if "github.com" in project_url:
        api = GhApi(owner=owner_name, repo=repo_name)
        try:
            latest_release = api.repos.get_latest_release()
        except Exception as e:
            logging.error(f"Failed to get latest release for repo: {project_url} \n Error: {e}")
            return {"is_released": False, "signature_files": [], "release_notes": []}, "Not found"

        latest_release_url = latest_release["zipball_url"]

    elif "gitee.com" in project_url:
        url = f"https://gitee.com/api/v5/repos/{owner_name}/{repo_name}/releases/latest"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                tag_name = response.json()["tag_name"]
                access_token = config["Gitee"]["access_key"]
                latest_release_url = f"https://gitee.com/api/v5/repos/{owner_name}/{repo_name}/zipball?access_token={access_token}&ref={tag_name}"
            else:
                logging.error(f"Failed to get latest release for repo: {project_url} \n Error: Not found")
                return {"is_released": False, "signature_files": [], "release_notes": []}, "Not found"
        except Exception as e:
            logging.error(f"Failed to get latest release for repo: {project_url} \n Error: {e}")
            return {"is_released": False, "signature_files": [], "release_notes": []}, "Not found"

    else:
        logging.info(f"Failed to do release files check for repo: {project_url} \n Error: Not supported platform.")
        return {"is_released": False, "signature_files": [], "release_notes": []}, "Not supported platform."

    response = requests.get(latest_release_url)
    if response.status_code != 200:
        return {"is_released": True, "signature_files": [], "release_notes": []}, "Failed to download release."

    signature_files = []
    changelog_files = []
    with zipfile.ZipFile(io.BytesIO(response.content), 'r') as zip_ref:
        signature_suffixes = ["*.asc", "*.sig", "*.cer", "*.crt", "*.pem", "*.sha256", "*.sha512"]
        signature_files = [file for file in zip_ref.namelist() if any(file.lower().endswith(suffix) for suffix in signature_suffixes)]

        changelog_names = ["changelog", "releasenotes", "release_notes"]
        changelog_files = [file for file in zip_ref.namelist() if any(name in os.path.basename(file).lower() for name in changelog_names)]

    return {"is_released": True, "signature_files": signature_files, "release_notes": changelog_files}, None

def callback_func(ch, method, properties, body):
    """
    Main callback function for processing analysis requests
    
    Args:
        ch: Channel object
        method: Method frame
        properties: Properties frame
        body: Message body
    """
    logging.info(f"Callback function called at {datetime.now()}")

    try:
    message = json.loads(body.decode('utf-8'))
    command_list = message.get('command_list')
    project_url = message.get('project_url')
    commit_hash = message.get("commit_hash")
    callback_url = message.get('callback_url')
    task_metadata = message.get('task_metadata')
    version_number = task_metadata.get("version_number", "None")
        logging.info(f"Processing project: {project_url}")

    res_payload = {
        "command_list": command_list,
        "project_url": project_url,
        "task_metadata": task_metadata,
            "scan_results": {}
    }

        # Download source code
        shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ ! -e "$project_name" ]; then
                    GIT_ASKPASS=/bin/true git clone {project_url}
                fi

                cd "$project_name"

                if [ {version_number} != "None" ]; then
                # Check if version number exists in git tags
                    if git tag | grep -q "^$version_number$"; then
                    # Switch to the specified tag
                        git checkout "$version_number"
                        if [ $? -eq 0 ]; then
                        echo "Successfully switched to tag $version_number"
                        else
                        echo "Failed to switch to tag $version_number"
                        fi
                    fi
                fi
            """

    result, error = shell_exec(shell_script)

        if error is None:
            logging.info(f"Source code download completed: {project_url}")
    else:
            logging.error(f"Source code download failed: {project_url}, error: {error}")
            logging.error(f"Moving message to dead letters: {body}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

        # Generate lock files for dependency analysis
        shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ -e "$project_name/package.json" ] && [ ! -e "$project_name/package-lock.json" ]; then
                    cd $project_name && npm install && rm -fr node_modules > /dev/null
                echo "Generated lock files for $project_name using npm"
                fi
                if [ -e "$project_name/oh-package.json5" ] && [ ! -e "$project_name/oh-package-lock.json5" ]; then
                    cd $project_name && ohpm install && rm -fr oh_modules > /dev/null
                echo "Generated lock files for $project_name using ohpm"
                fi
            """

    result, error = shell_exec(shell_script)

        if error is None:
            logging.info(f"Lock files generation completed: {result.decode('utf-8') if bool(result) else 'No lock files generated'}")
    else:
            logging.error(f"Lock files generation failed: {project_url}, error: {error}")

        # Process each command in the command list
    for command in command_list:
            try:
                process_command(command, project_url, commit_hash, res_payload)
            except Exception as e:
                logging.error(f"Error processing command {command}: {e}")
                res_payload["scan_results"][command] = {"error": str(e)}

        # Clean up source code
        shell_script = f"""
            project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
            if [ -e "$project_name" ]; then
                rm -rf $project_name > /dev/null
            fi
        """

        result, error = shell_exec(shell_script)

        if error is None:
            logging.info(f"Source code cleanup completed: {project_url}")
        else:
            logging.error(f"Source code cleanup failed: {project_url}, error: {error}")

        # Send results via callback URL if provided
        if callback_url:
            try:
                response = request_url(callback_url, res_payload)
                logging.info(f"Callback response: {response}")
            except Exception as e:
                logging.error(f"Error sending callback: {e}")
                logging.error(f"Moving message to dead letters: {body}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logging.error(f"Error in callback function: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def process_command(command: str, project_url: str, commit_hash: Optional[str], res_payload: Dict) -> None:
    """
    Process individual analysis command
    
    Args:
        command: Command to execute
        project_url: URL of the project repository
        commit_hash: Optional commit hash for version-specific analysis
        res_payload: Result payload to update
    """
        if command == 'osv-scanner':
        process_osv_scanner(project_url, res_payload)
    elif command == 'scancode':
        process_scancode(project_url, res_payload)
    elif command == 'binary-checker':
        process_binary_checker(project_url, res_payload)
    elif command == 'release-checker':
        process_release_checker(project_url, res_payload)
    elif command == 'url-checker':
        process_url_checker(project_url, res_payload)
    elif command == 'sonar-scanner':
        process_sonar_scanner(project_url, res_payload)
    elif command == 'dependency-checker':
        process_dependency_checker(project_url, res_payload)
    elif command == 'readme-checker':
        process_readme_checker(project_url, res_payload)
    elif command == 'maintainers-checker':
        process_maintainers_checker(project_url, res_payload)
    elif command == 'readme-opensource-checker':
        process_readme_opensource_checker(project_url, res_payload)
    elif command == 'build-doc-checker':
        process_build_doc_checker(project_url, res_payload)
    elif command == 'api-doc-checker':
        process_api_doc_checker(project_url, res_payload)
    elif command == 'languages-detector':
        process_languages_detector(project_url, res_payload)
    elif command == 'changed-files-since-commit-detector':
        process_changed_files_detector(project_url, commit_hash, res_payload)
    elif command == 'oat-scanner':
        process_oat_scanner(project_url, res_payload)
    else:
        logging.info(f"Unknown command: {command}")

def process_osv_scanner(project_url: str, res_payload: Dict) -> None:
    """
    Process OSV scanner command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
    shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ ! -e "$project_name" ]; then
                    GIT_ASKPASS=/bin/true git clone --depth=1 {project_url} > /dev/null
                fi

        # Rename oh-package-lock.json5 to package-lock.json for osv-scanner compatibility
                if [ -f "$project_name/oh-package-lock.json5" ] && [! -f "$project_name/package-lock.json" ]; then
                    mv $project_name/oh-package-lock.json5 $project_name/package-lock.json  > /dev/null
                    rename_flag = 1
                fi

                osv-scanner --format json -r $project_name > $project_name/result.json
                cat $project_name/result.json

                if [ -v rename_flag ]; then
                    mv $project_name/package-lock.json $project_name/oh-package-lock.json5  > /dev/null
                fi
            """

            result, error = shell_exec(shell_script)

    if error is None:
        logging.info(f"OSV scanner completed: {project_url}")
            osv_result = json.loads(result.decode('utf-8')) if bool(result) else {}
            res_payload["scan_results"]["osv-scanner"] = osv_result
    else:
        logging.error(f"OSV scanner failed: {project_url}, error: {error}")
        res_payload["scan_results"]["osv-scanner"] = {"error": str(error)}

def process_scancode(project_url: str, res_payload: Dict) -> None:
    """
    Process scancode command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
    shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ ! -e "$project_name" ]; then
                    GIT_ASKPASS=/bin/true git clone --depth=1 {project_url} > /dev/null
                fi
                scancode -lc --json-pp scan_result.json $project_name --license-score 90 -n 4 > /dev/null
                cat scan_result.json
                rm -rf scan_result.json > /dev/null
            """

            result, error = shell_exec(shell_script)

    if error is None:
        logging.info(f"Scancode completed: {project_url}")
                scancode_result = json.loads(result.decode('utf-8')) if bool(result) else {}
                res_payload["scan_results"]["scancode"] = scancode_result
            else:
        logging.error(f"Scancode failed: {project_url}, error: {error}")
        res_payload["scan_results"]["scancode"] = {"error": str(error)}

def process_binary_checker(project_url: str, res_payload: Dict) -> None:
    """
    Process binary checker command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
            result, error = shell_exec("./scripts/binary_checker.sh", project_url)

    if error is None:
        logging.info(f"Binary checker completed: {project_url}")
                result = result.decode('utf-8') if bool(result) else ""
                data_list = result.split('\n')
                binary_file_list = []
                binary_archive_list = []
                for data in data_list[:-1]:
                    if "Binary file found:" in data:
                        binary_file_list.append(data.split(": ")[1])
                    elif "Binary archive found:" in data:
                        binary_archive_list.append(data.split(": ")[1])
        binary_result = {
            "binary_file_list": binary_file_list,
            "binary_archive_list": binary_archive_list
        }
                res_payload["scan_results"]["binary-checker"] = binary_result
            else:
        logging.error(f"Binary checker failed: {project_url}, error: {error}")
        res_payload["scan_results"]["binary-checker"] = {"error": str(error)}

def process_release_checker(project_url: str, res_payload: Dict) -> None:
    """
    Process release checker command

    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
            result, error = check_release_content(project_url)

    if error is None:
        logging.info(f"Release checker completed: {project_url}")
                res_payload["scan_results"]["release-checker"] = result
            else:
        logging.error(f"Release checker failed: {project_url}, error: {error}")
                res_payload["scan_results"]["release-checker"] = {"error": error}

def process_url_checker(project_url: str, res_payload: Dict) -> None:
    """
    Process URL checker command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
            from urllib import request
            try:
                with request.urlopen(project_url) as file:
                    if file.status == 200 and file.reason == "OK":
                logging.info(f"URL checker completed: {project_url}")
                        url_result = {"url": project_url, "status": "pass", "error": "null"}
                    else:
                logging.error(f"URL checker failed: {project_url}")
                        url_result = {"url": project_url, "status": "fail", "error": file.reason}
            except Exception as e:
        logging.error(f"URL checker failed: {project_url}, error: {e}")
        url_result = {"error": str(e)}
            res_payload["scan_results"]["url-checker"] = url_result

def process_sonar_scanner(project_url: str, res_payload: Dict) -> None:
    """
    Process SonarQube scanner command

    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
            pattern = r'https?://(?:www\.)?(github\.com|gitee\.com|gitcode\.com)/([^/]+)/([^/]+)\.git'
            match = re.match(pattern, project_url)
            if match:
                platform, organization, project = match.groups()
            else:
                platform, organization, project = "other", "default", "default"
    sonar_project_name = f"{platform}_{organization}_{project}"

            sonar_config = config["SonarQube"]
    sonar_search_project_api = f"http://{sonar_config['host']}:{sonar_config['port']}/api/projects/search"
            auth = (sonar_config["username"], sonar_config["password"])
    is_exist = False

            try:
        response = requests.get(sonar_search_project_api, auth=auth, params={"projects": sonar_project_name})
                if response.status_code == 200:
            logging.info("SonarQube project search successful")
                    res = json.loads(response.text)
            is_exist = res["paging"]["total"] > 0
                else:
            logging.error(f"SonarQube project search failed: {response.status_code}")
            except requests.exceptions.RequestException as e:
        logging.error(f"SonarQube project search failed: {e}")

    if not is_exist:
        sonar_create_project_api = f"http://{sonar_config['host']}:{sonar_config['port']}/api/projects/create"
                data = {"project": sonar_project_name, "name": sonar_project_name}

                try:
            response = requests.post(sonar_create_project_api, auth=auth, data=data)
                    if response.status_code == 200:
                logging.info("SonarQube project creation successful")
                    else:
                logging.error(f"SonarQube project creation failed: {response.status_code}")
                except requests.exceptions.RequestException as e:
            logging.error(f"SonarQube project creation failed: {e}")

    shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ ! -e "$project_name" ]; then
                    GIT_ASKPASS=/bin/true git clone --depth=1 {project_url} > /dev/null
                fi
                cp -r $project_name ~/ && cd ~
                sonar-scanner \
                    -Dsonar.projectKey={sonar_project_name} \
                    -Dsonar.sources=$project_name \
                    -Dsonar.host.url=http://{sonar_config['host']}:{sonar_config['port']} \
                    -Dsonar.token={sonar_config['token']} \
                    -Dsonar.exclusions=**/*.java
                rm -rf $project_name > /dev/null
            """

            result, error = shell_exec(shell_script)

    if error is None:
        logging.info(f"SonarQube scanning completed: {project_url}, querying report...")

                sonar_query_measures_api = f"http://{sonar_config['host']}:{sonar_config['port']}/api/measures/component"

                try:
            # Wait for SonarQube data processing
                    time.sleep(60)
            response = requests.get(
                sonar_query_measures_api,
                auth=auth,
                params={
                    "component": sonar_project_name,
                    "metricKeys": "coverage,complexity,duplicated_lines_density,lines"
                }
            )
                    if response.status_code == 200:
                logging.info("SonarQube report query successful")
                        sonar_result = json.loads(response.text)
                        res_payload["scan_results"]["sonar-scanner"] = sonar_result
                    else:
                logging.error(f"SonarQube report query failed: {response.status_code}")
                except requests.exceptions.RequestException as e:
            logging.error(f"SonarQube report query failed: {e}")

        logging.info(f"SonarQube scanner completed: {project_url}")
            else:
        logging.error(f"SonarQube scanner failed: {project_url}, error: {error}")
        res_payload["scan_results"]["sonar-scanner"] = {"error": str(error)}

def process_dependency_checker(project_url: str, res_payload: Dict) -> None:
    """
    Process dependency checker command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
    shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ ! -e "$project_name" ]; then
                    GIT_ASKPASS=/bin/true git clone --depth=1 {project_url} > /dev/null
                fi
                ort -P ort.analyzer.allowDynamicVersions=true analyze -i $project_name -o $project_name -f JSON > /dev/null
                cat $project_name/analyzer-result.json
            """
            result, error = shell_exec(shell_script)

    if error is None:
        logging.info(f"Dependency checker completed: {project_url}")
                res_payload["scan_results"]["dependency-checker"] = dependency_checker_output_process(result)
            else:
        logging.error(f"Dependency checker failed: {project_url}, error: {error}")
        res_payload["scan_results"]["dependency-checker"] = {"error": str(error)}

def process_readme_checker(project_url: str, res_payload: Dict) -> None:
    """
    Process README checker command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
    shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ ! -e "$project_name" ]; then
                    GIT_ASKPASS=/bin/true git clone --depth=1 {project_url} > /dev/null
                fi
                find "$project_name" -type f \( -name "README*" -o -name ".github/README*" -o -name "docs/README*" \) -print
            """

            result, error = shell_exec(shell_script)

    if error is None:
        logging.info(f"README checker completed: {project_url}")
        res_payload["scan_results"]["readme-checker"] = {
            "readme_file": result.decode('utf-8').split('\n')[:-1]
        } if bool(result) else {}
            else:
        logging.error(f"README checker failed: {project_url}, error: {error}")
        res_payload["scan_results"]["readme-checker"] = {"error": str(error)}

def process_maintainers_checker(project_url: str, res_payload: Dict) -> None:
    """
    Process maintainers checker command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
    shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ ! -e "$project_name" ]; then
                    GIT_ASKPASS=/bin/true git clone --depth=1 {project_url} > /dev/null
                fi
                find "$project_name" -type f \( -iname "MAINTAINERS*" -o -iname "COMMITTERS*" -o -iname "OWNERS*" -o -iname "CODEOWNERS*" \) -print
            """

            result, error = shell_exec(shell_script)

    if error is None:
        logging.info(f"Maintainers checker completed: {project_url}")
        res_payload["scan_results"]["maintainers-checker"] = {
            "maintainers_file": result.decode('utf-8').split('\n')[:-1]
        } if bool(result) else {}
            else:
        logging.error(f"Maintainers checker failed: {project_url}, error: {error}")
        res_payload["scan_results"]["maintainers-checker"] = {"error": str(error)}

def process_readme_opensource_checker(project_url: str, res_payload: Dict) -> None:
    """
    Process README.OpenSource checker command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
    result, error = check_readme_opensource(project_url)
    if error is None:
        logging.info(f"README.OpenSource checker completed: {project_url}")
        res_payload["scan_results"]["readme-opensource-checker"] = {
            "readme-opensource-checker": result
        } if bool(result) else {}
            else:
        logging.error(f"README.OpenSource checker failed: {project_url}, error: {error}")
        res_payload["scan_results"]["readme-opensource-checker"] = {"error": error}

def process_build_doc_checker(project_url: str, res_payload: Dict) -> None:
    """
    Process build documentation checker command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
    result, error = check_doc_content(project_url, "build-doc")
    if error is None:
        logging.info(f"Build documentation checker completed: {project_url}")
        res_payload["scan_results"]["build-doc-checker"] = {
            "build-doc-checker": result
        } if bool(result) else {}
            else:
        logging.error(f"Build documentation checker failed: {project_url}, error: {error}")
        res_payload["scan_results"]["build-doc-checker"] = {"error": error}

def process_api_doc_checker(project_url: str, res_payload: Dict) -> None:
    """
    Process API documentation checker command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
    result, error = check_doc_content(project_url, "api-doc")
    if error is None:
        logging.info(f"API documentation checker completed: {project_url}")
        res_payload["scan_results"]["api-doc-checker"] = {
            "api-doc-checker": result
        } if bool(result) else {}
            else:
        logging.error(f"API documentation checker failed: {project_url}, error: {error}")
        res_payload["scan_results"]["api-doc-checker"] = {"error": error}

def process_languages_detector(project_url: str, res_payload: Dict) -> None:
    """
    Process programming languages detector command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
    shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ ! -e "$project_name" ]; then
                    GIT_ASKPASS=/bin/true git clone --depth=1 {project_url} > /dev/null
                fi
                github-linguist $project_name --breakdown --json
            """

            result, error = shell_exec(shell_script)

    if error is None:
        logging.info(f"Languages detector completed: {project_url}")
                res_payload["scan_results"]["languages-detector"] = json.dumps(result.decode("utf-8")) if bool(result) else {}
            else:
        logging.error(f"Languages detector failed: {project_url}, error: {error}")
        res_payload["scan_results"]["languages-detector"] = {"error": str(error)}

def process_changed_files_detector(project_url: str, commit_hash: Optional[str], res_payload: Dict) -> None:
    """
    Process changed files detector command
    
    Args:
        project_url: URL of the project repository
        commit_hash: Optional commit hash for version-specific analysis
        res_payload: Result payload to update
    """
            if commit_hash is None:
        logging.error("Failed to get commit hash from message body!")
        return

            context_path = os.getcwd()
            try:
                repository_path = os.path.join(context_path, os.path.splitext(os.path.basename(urlparse(project_url).path))[0])
                os.chdir(repository_path)
        logging.info(f"Changed directory to git repository: {repository_path}")
            except OSError as e:
        logging.error(f"Failed to change directory to git repository: {e}")
        return

    def get_diff_files(type: str = "ACDMRTUXB") -> List[str]:
        """
        Get files changed in git diff
        
        Args:
            type: Git diff filter type
            
        Returns:
            List of changed files
        """
                try:
                    result = subprocess.check_output(
                       ["git", "diff", "--name-only", f"--diff-filter={type}", f"{commit_hash}..HEAD"],
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    return result.strip().split("\n") if result else []
                except subprocess.CalledProcessError as e:
            logging.error(f"Failed to get {type} files: {e.output}")
                    return []

            changed_files = get_diff_files()
            new_files = get_diff_files("A")
            rename_files = get_diff_files("R")
            deleted_files = get_diff_files("D")
            modified_files = get_diff_files("M")

            os.chdir(context_path)

            res_payload["scan_results"]["changed-files-since-commit-detector"] = {
                "changed_files": changed_files,
                "new_files": new_files,
                "rename_files": rename_files,
                "deleted_files": deleted_files,
                "modified_files": modified_files
                }

def process_oat_scanner(project_url: str, res_payload: Dict) -> None:
    """
    Process OAT scanner command
    
    Args:
        project_url: URL of the project repository
        res_payload: Result payload to update
    """
            shell_script = f"""
                project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null
                if [ ! -e "$project_name" ]; then
                    GIT_ASKPASS=/bin/true git clone --depth=1 {project_url} > /dev/null
                fi                
                if [ ! -f "$project_name/OAT.xml" ]; then
                    echo "OAT.xml not found in the project root directory."
                    exit 1   
                fi
        java -jar ohos_ossaudittool-2.0.0.jar -mode s -s $project_name -r $project_name/oat_out -n $project_name > /dev/null            
                report_file="$project_name/oat_out/single/PlainReport_$project_name.txt"
                if [ -f "$report_file" ]; then                    
                    cat "$report_file"                                    
                fi                        
            """
            result, error = shell_exec(shell_script)
            
    if error is None:
        logging.info(f"OAT scanner completed: {project_url}")
            else:
        logging.error(f"OAT scanner failed: {project_url}, error: {error}")

    def parse_oat_txt_to_json(txt: bytes) -> Dict:
        """
        Parse OAT report text to JSON format
        
        Args:
            txt: Raw OAT report text
            
        Returns:
            Parsed OAT report in JSON format
        """
                try:
                    de_str = txt.decode('unicode_escape')
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
            logging.error(f"Failed to parse OAT report: {e}")
            return {"error": str(e)}

            res_payload["scan_results"]["oat-scanner"] = {}
            if not result:
        logging.info(f"OAT.xml not found: {project_url}")
                res_payload["scan_results"]["oat-scanner"] = {
                    "status_code": 404,
                    "error": "OAT.xml not found"
                }
            else:
                parse_res = parse_oat_txt_to_json(result)
                if error is None:
            logging.info(f"OAT scanner completed: {project_url}")
                    res_payload["scan_results"]["oat-scanner"] = parse_res
                    res_payload["scan_results"]["oat-scanner"]["status_code"] = 200
                else:
            logging.error(f"OAT scanner failed: {project_url}, error: {error}")
                    res_payload["scan_results"]["oat-scanner"] = {
                        "status_code": 500,
                "error": str(error)
            }

if __name__ == "__main__":
    consumer(config["RabbitMQ"], "opencheck", callback_func)
    logging.info('Agent server ended.')
