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
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import shlex

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s : %(message)s')

def load_config(config_path: Optional[str] = None) -> Dict:
    if config_path is None:
        config_path = os.getenv('CONFIG_PATH', 'config/config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
    return read_config(config_path)

@dataclass
class ProjectInfo:
    """Project information data class"""
    url: str
    name: str
    owner: str
    repo: str
    platform: str

class ProjectManager:
    """Project manager class"""
    def __init__(self, project_url: str):
        self.project_url = project_url
        self.project_info = self._parse_project_url()
        self.project_path = Path(self.project_info.name)

    def _parse_project_url(self) -> ProjectInfo:
        """Parse project URL and extract relevant information"""
        pattern = r'https?://(?:www\.)?(github\.com|gitee\.com|gitcode\.com)/([^/]+)/([^/]+)\.git'
        match = re.match(pattern, self.project_url)
        if not match:
            raise ValueError(f"Invalid project URL format: {self.project_url}")
        
        platform, owner, repo = match.groups()
        name = repo.replace('.git', '')
        return ProjectInfo(self.project_url, name, owner, repo, platform)

    def clone_if_not_exists(self) -> None:
        """Clone the project if it doesn't exist"""
        try:
            if not self.project_path.exists():
                result = subprocess.run(
                    ["git", "clone", "--depth=1", self.project_url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                logging.info(f"Successfully cloned repository: {self.project_url}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to clone repository: {e.stderr}")
            raise

    def cleanup(self) -> None:
        """Clean up project directory"""
        if self.project_path.exists():
            subprocess.run(["rm", "-rf", str(self.project_path)], check=True)

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get file content"""
        try:
            full_path = self.project_path / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except UnicodeDecodeError:
            logging.error(f"Failed to decode file: {file_path}")
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
        return None

    def find_files(self, patterns: List[str], search_dirs: List[str] = None) -> List[str]:
        """Find files matching specific patterns"""
        if search_dirs is None:
            search_dirs = [str(self.project_path)]
        
        found_files = []
        for directory in search_dirs:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
                
            for pattern in patterns:
                found_files.extend(str(f) for f in dir_path.glob(pattern))
        
        return found_files

def get_licenses_name(data):
    return next(
        (license['meta']['title'] 
         for license in data.get('licenses', []) 
         if license.get('meta', {}).get('title')), 
        None
    )

def ruby_licenses(data):
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
            # If a valid GitHub URL is found, clone the repository and call licensee
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
                if error == None:
                    try:
                        license_info = json.loads(result)
                        licenses_name = get_licenses_name(license_info)
                        item['declared_licenses'].append(licenses_name)
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse JSON from {project_url}: {e}")
                else:
                    logging.error("ruby_licenses job failed: {}, error: {}".format(project_url, error))
    return data

def dependency_checker_output_process(output):
    if not bool(output):
        return {}

    result = json.loads(output.decode('utf-8'))
    result = ruby_licenses(result)
    try:
        packages = result["analyzer"]["result"]["packages"]
        result = {"packages_all": [], "packages_with_license_detect": [], "packages_without_license_detect": []}

        for package in packages:
            result["packages_all"].append(package["purl"])
            license = package["declared_licenses"]
            if license != None and len(license) > 0:
                result["packages_with_license_detect"].append(package["purl"])
            else:
                result["packages_without_license_detect"].append(package["purl"])

    except Exception as e:
        logging.error(f"Error processing dependency-checker output: {e}")
        return {}

    return result

def safe_shell_exec(command: str, args: Optional[List[str]] = None) -> Tuple[Optional[str], Optional[str]]:
    try:
        if args:
            command = shlex.quote(command)
            args = [shlex.quote(arg) for arg in args]
            process = subprocess.Popen(
                [command] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
        stdout, stderr = process.communicate()
        return stdout, stderr
    except Exception as e:
        logging.error(f"Error executing command: {e}")
        return None, str(e)

def request_url (url, payload):
    response = post_with_backoff(url=url, json=payload)

    if response.status_code == 200:
        logging.info("Request sent successfully.")
        return response.text
    else:
        logging.error(f"Failed to send request. Status code: {response.status_code}")
        return None

def check_readme_opensource(project_url: str) -> Tuple[bool, Optional[str]]:
    """Check project's README.OpenSource file
    
    Args:
        project_url: Project URL
        
    Returns:
        Tuple[bool, Optional[str]]: (is valid, error message)
    """
    try:
        project = ProjectManager(project_url)
        project.clone_if_not_exists()
        
        content = project.get_file_content("README.OpenSource")
        if not content:
            return False, "README.OpenSource does not exist."
            
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                return False, "README.OpenSource is not properly formatted."
                
            required_keys = [
                "Name", "License", "License File",
                "Version Number", "Owner", "Upstream URL", "Description"
            ]
            
            if all(
                isinstance(entry, dict) and all(key in entry for key in required_keys)
                for entry in data
            ):
                return True, None
            return False, "The README.OpenSource file exists and is not properly formatted."
            
        except json.JSONDecodeError:
            return False, "README.OpenSource is not properly formatted."
            
    except Exception as e:
        logging.error(f"Error checking README.OpenSource: {e}")
        return False, str(e)
    finally:
        project.cleanup()

def check_doc_content(project_url: str, doc_type: str) -> Tuple[List[str], Optional[str]]:
    """Check project documentation content
    
    Args:
        project_url: Project URL
        doc_type: Document type ("build-doc" or "api-doc")
        
    Returns:
        Tuple[List[str], Optional[str]]: (document file list, error message)
    """
    if doc_type not in ["build-doc", "api-doc"]:
        return [], f"Unsupported document type: {doc_type}"
        
    try:
        project = ProjectManager(project_url)
        project.clone_if_not_exists()
        
        # Define document templates
        templates = {
            "build-doc": """
                You are a professional programmer, please assess whether the provided text offers a thorough and in-depth introduction to the processes of software compilation and packaging.
                If the text segment introduce the software compilation and packaging completely, please return 'YES'; otherwise, return 'NO'.
                You need to ensure the accuracy of your answers as much as possible, and if unsure, please simply answer NO. Your response must not include other content.

                Text content as below:

                {text}
            """,
            "api-doc": """
                You are a professional programmer, please assess whether the provided text offer a comprehensive introduction to the use of software API.
                If the text segment introduce the software API completely, please return 'YES'; otherwise, return 'NO'.
                You need to ensure the accuracy of your answers as much as possible, and if unsure, please simply answer NO. Your response must not include other content.

                Text content as below:

                {text}
            """
        }
        
        # Find document files
        search_dirs = [
            str(project.project_path),
            str(project.project_path / "doc"),
            str(project.project_path / "docs")
        ]
        
        doc_files = project.find_files(
            patterns=["**/*.md", "**/*.markdown"],
            search_dirs=search_dirs
        )
        
        found_docs = []
        for doc_file in doc_files:
            content = project.get_file_content(doc_file)
            if not content:
                continue
                
            # Check external links
            if doc_type == "build-doc":
                external_link = "https://gitee.com/openharmony-tpc/docs/blob/master/OpenHarmony_har_usage.md"
                if external_link.lower() in content.lower():
                    return found_docs, None
            
            # Process large files in chunks
            chunk_size = 3000
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            
            for chunk in chunks:
                messages = [{
                    "role": "user",
                    "content": templates[doc_type].format(text=chunk)
                }]
                
                result = completion_with_backoff(messages=messages, temperature=0.2)
                if result == "YES":
                    found_docs.append(doc_file)
                    return found_docs, None
                    
        return found_docs, None
        
    except Exception as e:
        logging.error(f"Error checking document content: {e}")
        return [], str(e)
    finally:
        project.cleanup()

def check_release_content(project_url: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """Check project release content
    
    Args:
        project_url: Project URL
        
    Returns:
        Tuple[Dict[str, Any], Optional[str]]: (release information, error message)
    """
    try:
        project = ProjectManager(project_url)
        
        if project.project_info.platform == "github.com":
            api = GhApi(owner=project.project_info.owner, repo=project.project_info.repo)
            try:
                latest_release = api.repos.get_latest_release()
                latest_release_url = latest_release["zipball_url"]
            except Exception as e:
                logging.error(f"Failed to get latest release for repo: {project_url} \n Error: {e}")
                return {"is_released": False, "signature_files": [], "release_notes": []}, "Not found"
                
        elif project.project_info.platform == "gitee.com":
            url = f"https://gitee.com/api/v5/repos/{project.project_info.owner}/{project.project_info.repo}/releases/latest"
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    return {"is_released": False, "signature_files": [], "release_notes": []}, "Not found"
                    
                tag_name = response.json()["tag_name"]
                access_token = config["Gitee"]["access_key"]
                latest_release_url = (
                    f"https://gitee.com/api/v5/repos/{project.project_info.owner}/"
                    f"{project.project_info.repo}/zipball?access_token={access_token}&ref={tag_name}"
                )
            except Exception as e:
                logging.error(f"Failed to get latest release for repo: {project_url} \n Error: {e}")
                return {"is_released": False, "signature_files": [], "release_notes": []}, "Not found"
        else:
            return {"is_released": False, "signature_files": [], "release_notes": []}, "Unsupported platform"
            
        # Download and check release package
        response = requests.get(latest_release_url)
        if response.status_code != 200:
            return {"is_released": True, "signature_files": [], "release_notes": []}, "Failed to download release"
            
        signature_files = []
        changelog_files = []
        
        with zipfile.ZipFile(io.BytesIO(response.content), 'r') as zip_ref:
            # Check signature files
            signature_suffixes = ["*.asc", "*.sig", "*.cer", "*.crt", "*.pem", "*.sha256", "*.sha512"]
            signature_files = [
                file for file in zip_ref.namelist()
                if any(file.lower().endswith(suffix.replace("*", "")) for suffix in signature_suffixes)
            ]
            
            # Check changelog files
            changelog_names = ["changelog", "releasenotes", "release_notes"]
            changelog_files = [
                file for file in zip_ref.namelist()
                if any(name in os.path.basename(file).lower() for name in changelog_names)
            ]
            
        return {
            "is_released": True,
            "signature_files": signature_files,
            "release_notes": changelog_files
        }, None
        
    except Exception as e:
        logging.error(f"Error checking release content: {e}")
        return {"is_released": False, "signature_files": [], "release_notes": []}, str(e)

def callback_func(ch, method, properties, body):
    """Process message queue callback
    
    Args:
        ch: Channel object
        method: Method object
        properties: Properties object
        body: Message body
    """
    logging.info(f"callback func called at {datetime.now()}")

    try:
        message = json.loads(body.decode('utf-8'))
        command_list = message.get('command_list', [])
        project_url = message.get('project_url')
        commit_hash = message.get("commit_hash")
        callback_url = message.get('callback_url')
        task_metadata = message.get('task_metadata', {})
        version_number = task_metadata.get("version_number", "None")
        
        if not project_url:
            raise ValueError("Project URL is required")
            
        logging.info(f"Processing project: {project_url}")
        
        res_payload = {
            "command_list": command_list,
            "project_url": project_url,
            "task_metadata": task_metadata,
            "scan_results": {}
        }
        
        # Initialize project manager
        project = ProjectManager(project_url)
        
        try:
            # Clone project
            project.clone_if_not_exists()
            
            # If version number is specified, switch to that version
            if version_number != "None":
                subprocess.run(
                    ["git", "checkout", version_number],
                    cwd=str(project.project_path),
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Generate lock files
            if (project.project_path / "package.json").exists() and not (project.project_path / "package-lock.json").exists():
                subprocess.run(
                    ["npm", "install"],
                    cwd=str(project.project_path),
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ["rm", "-fr", "node_modules"],
                    cwd=str(project.project_path),
                    check=True
                )
                
            if (project.project_path / "oh-package.json5").exists() and not (project.project_path / "oh-package-lock.json5").exists():
                subprocess.run(
                    ["ohpm", "install"],
                    cwd=str(project.project_path),
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ["rm", "-fr", "oh_modules"],
                    cwd=str(project.project_path),
                    check=True
                )
            
            # Execute command list
            for command in command_list:
                try:
                    if command == 'osv-scanner':
                        result = run_osv_scanner(project)
                        res_payload["scan_results"]["osv-scanner"] = result
                        
                    elif command == 'scancode':
                        result = run_scancode(project)
                        res_payload["scan_results"]["scancode"] = result
                        
                    elif command == 'binary-checker':
                        result = run_binary_checker(project)
                        res_payload["scan_results"]["binary-checker"] = result
                        
                    elif command == 'release-checker':
                        result, error = check_release_content(project_url)
                        res_payload["scan_results"]["release-checker"] = result
                        
                    elif command == 'url-checker':
                        result = check_url(project_url)
                        res_payload["scan_results"]["url-checker"] = result
                        
                    elif command == 'sonar-scanner':
                        result = run_sonar_scanner(project)
                        res_payload["scan_results"]["sonar-scanner"] = result
                        
                    elif command == 'dependency-checker':
                        result = run_dependency_checker(project)
                        res_payload["scan_results"]["dependency-checker"] = result
                        
                    elif command == 'readme-checker':
                        result = run_readme_checker(project)
                        res_payload["scan_results"]["readme-checker"] = result
                        
                    elif command == 'maintainers-checker':
                        result = run_maintainers_checker(project)
                        res_payload["scan_results"]["maintainers-checker"] = result
                        
                    elif command == 'readme-opensource-checker':
                        result, error = check_readme_opensource(project_url)
                        res_payload["scan_results"]["readme-opensource-checker"] = result
                        
                    elif command == 'build-doc-checker':
                        result, error = check_doc_content(project_url, "build-doc")
                        res_payload["scan_results"]["build-doc-checker"] = result
                        
                    elif command == 'api-doc-checker':
                        result, error = check_doc_content(project_url, "api-doc")
                        res_payload["scan_results"]["api-doc-checker"] = result
                        
                    elif command == 'languages-detector':
                        result = run_languages_detector(project)
                        res_payload["scan_results"]["languages-detector"] = result
                        
                    elif command == 'changed-files-since-commit-detector':
                        if not commit_hash:
                            raise ValueError("Commit hash is required for changed-files-since-commit-detector")
                        result = run_changed_files_detector(project, commit_hash)
                        res_payload["scan_results"]["changed-files-since-commit-detector"] = result
                        
                    elif command == 'oat-scanner':
                        result = run_oat_scanner(project)
                        res_payload["scan_results"]["oat-scanner"] = result
                        
                    else:
                        logging.warning(f"Unknown command: {command}")
                        
                except Exception as e:
                    logging.error(f"Error executing command {command}: {e}")
                    res_payload["scan_results"][command] = {"error": str(e)}
            
            # Send callback
            if callback_url:
                response = request_url(callback_url, res_payload)
                if not response:
                    raise Exception("Failed to send callback")
                    
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        finally:
            project.cleanup()
            
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        logging.error(f"Message body: {body}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def run_osv_scanner(project: ProjectManager) -> Dict[str, Any]:
    """Run OSV scanner
    
    Args:
        project: Project manager instance
        
    Returns:
        Dict[str, Any]: Scan results
    """
    try:
        # Rename oh-package-lock.json5 to package-lock.json for osv-scanner to read
        if (project.project_path / "oh-package-lock.json5").exists() and not (project.project_path / "package-lock.json").exists():
            subprocess.run(
                ["mv", "oh-package-lock.json5", "package-lock.json"],
                cwd=str(project.project_path),
                check=True
            )
            rename_flag = True
        else:
            rename_flag = False
            
        # Run scan
        result = subprocess.run(
            ["osv-scanner", "--format", "json", "-r", str(project.project_path)],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Restore filename
        if rename_flag:
            subprocess.run(
                ["mv", "package-lock.json", "oh-package-lock.json5"],
                cwd=str(project.project_path),
                check=True
            )
            
        return json.loads(result.stdout)
        
    except subprocess.CalledProcessError as e:
        logging.error(f"OSV scanner failed: {e}")
        return {"error": str(e)}
    except Exception as e:
        logging.error(f"Error running OSV scanner: {e}")
        return {"error": str(e)}

def run_scancode(project: ProjectManager) -> Dict[str, Any]:
    """Run Scancode scanner
    
    Args:
        project: Project manager instance
        
    Returns:
        Dict[str, Any]: Scan results
    """
    try:
        result = subprocess.run(
            [
                "scancode",
                "-lc",
                "--json-pp", "scan_result.json",
                str(project.project_path),
                "--license-score", "90",
                "-n", "4"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        with open(project.project_path / "scan_result.json", "r") as f:
            return json.load(f)
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Scancode failed: {e}")
        return {"error": str(e)}
    except Exception as e:
        logging.error(f"Error running scancode: {e}")
        return {"error": str(e)}

def run_binary_checker(project: ProjectManager) -> Dict[str, Any]:
    """Run binary file checker
    
    Args:
        project: Project manager instance
        
    Returns:
        Dict[str, Any]: Check results
    """
    try:
        result = subprocess.run(
            ["./scripts/binary_checker.sh", str(project.project_path)],
            capture_output=True,
            text=True,
            check=True
        )
        
        binary_file_list = []
        binary_archive_list = []
        
        for line in result.stdout.splitlines():
            if "Binary file found:" in line:
                binary_file_list.append(line.split(": ")[1])
            elif "Binary archive found:" in line:
                binary_archive_list.append(line.split(": ")[1])
                
        return {
            "binary_file_list": binary_file_list,
            "binary_archive_list": binary_archive_list
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Binary checker failed: {e}")
        return {"error": str(e)}
    except Exception as e:
        logging.error(f"Error running binary checker: {e}")
        return {"error": str(e)}

def check_url(url: str) -> Dict[str, Any]:
    """Check URL accessibility
    
    Args:
        url: URL to check
        
    Returns:
        Dict[str, Any]: Check results
    """
    try:
        response = requests.head(url, allow_redirects=True)
        if response.status_code == 200:
            return {"url": url, "status": "pass", "error": None}
        return {"url": url, "status": "fail", "error": response.reason}
    except Exception as e:
        return {"url": url, "status": "fail", "error": str(e)}

def run_sonar_scanner(project: ProjectManager) -> Dict[str, Any]:
    """Run SonarQube scanner
    
    Args:
        project: Project manager instance
        
    Returns:
        Dict[str, Any]: Scan results
    """
    try:
        sonar_project_name = f"{project.project_info.platform}_{project.project_info.owner}_{project.project_info.repo}"
        sonar_config = config["SonarQube"]
        
        # Check if project exists
        auth = (sonar_config["username"], sonar_config["password"])
        search_url = f"http://{sonar_config['host']}:{sonar_config['port']}/api/projects/search"
        
        response = requests.get(search_url, auth=auth, params={"projects": sonar_project_name})
        if response.status_code != 200:
            raise Exception(f"Failed to search project: {response.status_code}")
            
        data = response.json()
        if data["paging"]["total"] == 0:
            # Create new project
            create_url = f"http://{sonar_config['host']}:{sonar_config['port']}/api/projects/create"
            response = requests.post(
                create_url,
                auth=auth,
                data={"project": sonar_project_name, "name": sonar_project_name}
            )
            if response.status_code != 200:
                raise Exception(f"Failed to create project: {response.status_code}")
                
        # Run scan
        subprocess.run(
            [
                "sonar-scanner",
                f"-Dsonar.projectKey={sonar_project_name}",
                f"-Dsonar.sources={project.project_path}",
                f"-Dsonar.host.url=http://{sonar_config['host']}:{sonar_config['port']}",
                f"-Dsonar.token={sonar_config['token']}",
                "-Dsonar.exclusions=**/*.java"
            ],
            check=True
        )
        
        # Wait for processing to complete
        time.sleep(60)
        
        # Get results
        measures_url = f"http://{sonar_config['host']}:{sonar_config['port']}/api/measures/component"
        response = requests.get(
            measures_url,
            auth=auth,
            params={
                "component": sonar_project_name,
                "metricKeys": "coverage,complexity,duplicated_lines_density,lines"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get measures: {response.status_code}")
            
        return response.json()
        
    except Exception as e:
        logging.error(f"Error running sonar scanner: {e}")
        return {"error": str(e)}

def run_dependency_checker(project: ProjectManager) -> Dict[str, Any]:
    """Run dependency checker
    
    Args:
        project: Project manager instance
        
    Returns:
        Dict[str, Any]: Check results
    """
    try:
        result = subprocess.run(
            [
                "ort",
                "-P", "ort.analyzer.allowDynamicVersions=true",
                "analyze",
                "-i", str(project.project_path),
                "-o", str(project.project_path),
                "-f", "JSON"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        with open(project.project_path / "analyzer-result.json", "r") as f:
            return dependency_checker_output_process(f.read().encode())
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Dependency checker failed: {e}")
        return {"error": str(e)}
    except Exception as e:
        logging.error(f"Error running dependency checker: {e}")
        return {"error": str(e)}

def run_readme_checker(project: ProjectManager) -> Dict[str, Any]:
    """Run README checker
    
    Args:
        project: Project manager instance
        
    Returns:
        Dict[str, Any]: Check results
    """
    try:
        readme_files = project.find_files(
            patterns=["**/README*", "**/.github/README*", "**/docs/README*"]
        )
        return {"readme_file": readme_files}
    except Exception as e:
        logging.error(f"Error running readme checker: {e}")
        return {"error": str(e)}

def run_maintainers_checker(project: ProjectManager) -> Dict[str, Any]:
    """Run maintainers checker
    
    Args:
        project: Project manager instance
        
    Returns:
        Dict[str, Any]: Check results
    """
    try:
        maintainer_files = project.find_files(
            patterns=["**/MAINTAINERS*", "**/COMMITTERS*", "**/OWNERS*", "**/CODEOWNERS*"]
        )
        return {"maintainers_file": maintainer_files}
    except Exception as e:
        logging.error(f"Error running maintainers checker: {e}")
        return {"error": str(e)}

def run_languages_detector(project: ProjectManager) -> Dict[str, Any]:
    """Run language detector
    
    Args:
        project: Project manager instance
        
    Returns:
        Dict[str, Any]: Detection results
    """
    try:
        result = subprocess.run(
            ["github-linguist", str(project.project_path), "--breakdown", "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logging.error(f"Languages detector failed: {e}")
        return {"error": str(e)}
    except Exception as e:
        logging.error(f"Error running languages detector: {e}")
        return {"error": str(e)}

def run_changed_files_detector(project: ProjectManager, commit_hash: str) -> Dict[str, Any]:
    """Run changed files detector
    
    Args:
        project: Project manager instance
        commit_hash: Commit hash value
        
    Returns:
        Dict[str, Any]: Detection results
    """
    try:
        def get_diff_files(type: str = "ACDMRTUXB") -> List[str]:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"--diff-filter={type}", f"{commit_hash}..HEAD"],
                cwd=str(project.project_path),
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split("\n") if result.stdout else []
            
        return {
            "changed_files": get_diff_files(),
            "new_files": get_diff_files("A"),
            "rename_files": get_diff_files("R"),
            "deleted_files": get_diff_files("D"),
            "modified_files": get_diff_files("M")
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Changed files detector failed: {e}")
        return {"error": str(e)}
    except Exception as e:
        logging.error(f"Error running changed files detector: {e}")
        return {"error": str(e)}

def run_oat_scanner(project: ProjectManager) -> Dict[str, Any]:
    """Run OAT scanner
    
    Args:
        project: Project manager instance
        
    Returns:
        Dict[str, Any]: Scan results
    """
    try:
        if not (project.project_path / "OAT.xml").exists():
            return {
                "status_code": 404,
                "error": "OAT.xml not found"
            }
            
        # Run scan
        subprocess.run(
            [
                "java", "-jar", "ohos_ossaudittool-2.0.0.jar",
                "-mode", "s",
                "-s", str(project.project_path),
                "-r", str(project.project_path / "oat_out"),
                "-n", project.project_info.name
            ],
            check=True
        )
        
        # Read report
        report_file = project.project_path / "oat_out" / "single" / f"PlainReport_{project.project_info.name}.txt"
        if not report_file.exists():
            return {
                "status_code": 500,
                "error": "Report file not found"
            }
            
        with open(report_file, "r") as f:
            content = f.read()
            
        # Parse report
        result = {}
        current_section = None
        pattern = r"Name:\s*(.+?)\s*Content:\s*(.+?)\s*Line:\s*(\d+)\s*Project:\s*(.+?)\s*File:\s*(.+)"
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
                
            total_count_match = re.search(r"^(.*) Total Count:\s*(\d+)", line, re.MULTILINE)
            if total_count_match:
                current_section = total_count_match.group(1).strip()
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
                    
        result["status_code"] = 200
        return result
        
    except subprocess.CalledProcessError as e:
        logging.error(f"OAT scanner failed: {e}")
        return {"status_code": 500, "error": str(e)}
    except Exception as e:
        logging.error(f"Error running OAT scanner: {e}")
        return {"status_code": 500, "error": str(e)}

if __name__ == "__main__":
    consumer(config["RabbitMQ"], "opencheck", callback_func)
    logging.info('Agents server ended.')
