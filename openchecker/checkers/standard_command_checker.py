import os
import subprocess
import json
import re
import requests
import yaml
from typing import Dict, Tuple, Any
from logger import get_logger
from platform_adapter import platform_manager

logger = get_logger('openchecker.checkers.standard_command_checker')


def run_criticality_score(project_url: str, config: dict) -> Tuple[Dict, str]:
    """
    Run criticality score analysis
    
    Args:
        project_url: Project URL
        config: Configuration dictionary
        
    Returns:
        Tuple[Dict, str]: (result, error)
    """
    if "github.com" in project_url:
        cmd = ["criticality_score", "--repo", project_url, "--format", "json"]
        github_token = config["Github"]["access_key"]
        os.environ['GITHUB_AUTH_TOKEN'] = github_token
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            json_str = result.stderr
            json_str = json_str.replace("\n", "")
            pattern = r'{.*?}'
            match = re.search(pattern, json_str)
            json_res = {}
            if match:
                json_score = match.group()
                try:
                    json_res = json.loads(json_score)
                    criticality_score = json_res['criticality_score']
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse criticality score JSON: {e}")
                    return None, "Failed to parse criticality score JSON."
                return {"criticality_score": criticality_score}, None
        else:
            logger.error(f"Criticality score command failed: {result.stderr}")
            return None, "Criticality score command failed."
    else:
        return None, "URL is not supported by criticality score."


def run_scorecard_cli(project_url: str) -> Tuple[Dict, str]:
    """
    Run scorecard CLI analysis
    
    Args:
        project_url: Project URL
        
    Returns:
        Tuple[Dict, str]: (result, error)
    """
    if "github.com" in project_url:
        cmd = ["scorecard", "--repo", project_url, "--format", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                scorecard_json = json.loads(result.stdout)
                scorecard_json = simplify_scorecard(scorecard_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse scorecard JSON: {e}")
                return None, "Failed to parse scorecard JSON."
            return scorecard_json, None
        else:
            logger.error(f"Scorecard command failed: {result.stderr}")
            return None, "Scorecard command failed."
    else:
        return None, "URL is not supported by scorecard CLI."


def simplify_scorecard(data: Dict) -> Dict:
    """
    Simplify scorecard data
    
    Args:
        data: Original scorecard data
        
    Returns:
        Dict: Simplified scorecard data
    """
    simplified = {
        "score": data["score"],
        "checks": []
    }
    if data["checks"] is not None:
        for check in data["checks"]:
            simplified_check = {
                "name": check["name"],
                "score": check["score"]
            }
            simplified["checks"].append(simplified_check)
    
    return simplified


def get_code_count(project_url: str) -> Tuple[Dict, str]:
    """
    Get code count using cloc
    
    Args:
        project_url: Project URL
        
    Returns:
        Tuple[Dict, str]: (result, error)
    """
    project_name = os.path.basename(project_url).replace('.git', '')

    if not os.path.exists(project_name):
        subprocess.run(["git", "clone", project_url, "--depth=1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cmd = ["cloc", project_name, "--json"] 
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        if result.stdout.strip() == "":
            return {"code_count": 0}, None
        result_json = json.loads(result.stdout)
        code_count = result_json['SUM']['code']
        return {"code_count": code_count}, None
    else:
        return None, "Failed to get code count."


def get_package_info(project_url: str) -> Tuple[Dict, str]:
    """
    Get package information
    
    Args:
        project_url: Project URL
        
    Returns:
        Tuple[Dict, str]: (result, error)
    """
    urlList = project_url.split("/")
    package_name = urlList[len(urlList) - 1]
    url = f"https://registry.npmjs.org/{package_name}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'github.com' in project_url:
            repo_info, repo_error = platform_manager.get_repo_info(project_url)
            if repo_error:
                logger.error(f"Failed to get repo info for {project_url}: {repo_error}")
                return {"description": False, "home_url": False, "dependent_count": False, "down_count": False, "day_enter": False}, repo_error
            description = repo_info.get("description", "")
            home_url = repo_info.get("homepage", "")
        else:
            description = data['description']
            home_url = data['homepage']
        version_data = data["versions"]
        *_, last_version = version_data.items()
        dependency = last_version[1].get("dependencies", {})
        dependent_count = len(dependency)
        
        url_down = f"https://api.npmjs.org/downloads/range/last-month/{package_name}"
        response_down = requests.get(url_down)
        if response_down.status_code == 200:
            down_data = response_down.json()
            last_month = down_data['downloads']
            down_count = 0
            for ch in last_month:
                down_count += ch['downloads']
            day_enter = last_month[0]['day'] + " - " + last_month[len(last_month) - 1]['day']   
            return {
                "description": description, 
                "home_url": home_url, 
                "dependent_count": dependent_count, 
                "down_count": down_count, 
                "day_enter": day_enter
            }, None
        elif response.status_code == 404:
            logger.error("Failed to get down_count for package: {} \n Error: Not found".format(package_name))
            return {"description": False, "home_url": False, "dependent_count": False, "down_count": False, "day_enter": False}, "Not found"
    else:
        # Use platform adapter to get repo info
        try:
            repo_info, repo_error = platform_manager.get_repo_info(project_url)
            download_stats, download_error = platform_manager.get_download_stats(project_url)
            
            if repo_error:
                logger.error(f"Failed to get repo info for {project_url}: {repo_error}")
                return {"description": False, "home_url": False, "dependent_count": False, "down_count": False, "day_enter": False}, repo_error
                
            description = repo_info.get("description", "")
            home_url = repo_info.get("homepage", "")
            down_count = download_stats.get("download_count", 0)
            day_enter = download_stats.get("period", "")
            
            return {
                "description": description, 
                "home_url": home_url, 
                "dependent_count": False, 
                "down_count": down_count, 
                "day_enter": day_enter
            }, None
        except Exception as e:
            logger.error(f"Failed to get package info for {project_url}: {e}")
            return {"description": False, "home_url": False, "dependent_count": False, "down_count": False, "day_enter": False}, str(e)


def get_ohpm_info(project_url: str) -> Tuple[Dict, str]:
    """
    Get OHPM package information
    
    Args:
        project_url: Project URL
        
    Returns:
        Tuple[Dict, str]: (result, error)
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        abs_dir = os.path.dirname(os.path.dirname(script_dir))
        file_path = os.path.join(abs_dir, 'config', 'ohpm_repo.json')
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        project_url = project_url.replace('.git', '')
        for name, repo_address in data.items():
            if repo_address.lower() == project_url.lower():
                url = 'https://ohpm.openharmony.cn/ohpmweb/registry/oh-package/openapi/v1/detail/'+ name
                response = requests.get(url)
                if response.status_code == 200:
                    repo_body = json.loads(response.text)
                    repo_json = repo_body['body']
                    down_count = repo_json['downloads']
                    dependent = repo_json['dependencies']['total']
                    bedependent = repo_json['dependent']['total']
                    return {"down_count": down_count, "dependent": dependent, "bedependent": bedependent}, None
                else:
                    logger.error("Failed to get dependent、bedependent、down_count for repo: {} \n Error: {}".format(project_url, "Not found"))
                    return {"down_count": False, "dependent": False, "bedependent": False}, "Not found"
        return {"down_count": "", "dependent": "", "bedependent": ""}, None
    except Exception as e:
        logger.error("parse_oat_txt error: {}".format(e))
        return {"down_count": "", "dependent": "", "bedependent": ""}, None

def get_type_countries(project_url, type) -> Tuple[Dict, str]:
    """
    获取仓库'type'的国家分布信息
    文档链接：https://ossinsight.io/docs/api/

    Args:
        project_url: 仓库地址
        type (str): 变更类型，可以是: issue_creators, pull_request_creators, stargazers(仓库维度).
    
    Returns:
        list: 仓库'type'的国家分布信息数组
    """
    try:
        if "github.com" in project_url:
            project_url = project_url.replace('.git', '')
            owner_name, repo_name = platform_manager.parse_project_url(project_url)
            url = f'https://api.ossinsight.io/v1/repos/{owner_name}/{repo_name}/{type}/countries/'
            response = requests.get(url)
            if response.status_code == 200:
                data_body = json.loads(response.text)
                data_json = data_body['data']
                return data_json, None
            else:
                logger.error("Failed to get {}_countries for repo: {} \n Error: {}".format(type, project_url, "Not found"))
                return False, "Not found"
        else:
            logger.error("Unsupported platform for {}_countries: {}".format(type, project_url))
            return False, "Unsupported platform"
    except Exception as e:
        logger.error("get_{}_countries error: {}".format(type, e))
        return False, None

def get_type_organizations(project_url, type)  -> Tuple[Dict, str]:
    """
    获取仓库'type'的组织分布信息
    文档链接：https://ossinsight.io/docs/api/

    Args:
        project_url: 仓库地址
        type (str): 变更类型，可以是: issue_creators, pull_request_creators, stargazers(仓库维度).
    
    Returns:
        list: 仓库'type'的组织分布信息数组
    """
    try:
        if "github.com" in project_url:           
            project_url = project_url.replace('.git', '')
            owner_name, repo_name = platform_manager.parse_project_url(project_url)
            url = f'https://api.ossinsight.io/v1/repos/{owner_name}/{repo_name}/{type}/organizations/'
            response = requests.get(url)
            if response.status_code == 200:
                data_body = json.loads(response.text)
                data_json = data_body['data']
                return data_json, None
            else:
                logger.error("Failed to get {}_organizations for repo: {} \n Error: {}".format(type, project_url, "Not found"))
                return False, "Not found"
        else:
            logger.error("Unsupported platform for {}_organizations: {}".format(type, project_url))
            return False, "Unsupported platform"
    except Exception as e:
        logger.error("get_{}_organizations error: {}".format(type, e))
        return False, None

def get_eol_info(project_url: str) -> Tuple[Dict, str]:
    """
    Get end-of-life (EOL) information

    Args:
        project_url: Project URL
        
    Returns:
        Tuple[Dict, str]: (result, error)
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        abs_dir = os.path.dirname(os.path.dirname(script_dir))
        file_path = os.path.join(abs_dir, 'config', 'eol.yaml')
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        eol_list = data.get("EOL LIST", {})
        project_url = project_url.replace('.git', '')
        for item in eol_list:
            if item['identifier'] == project_url:
                eol_status = item['eol']
                eol_release = item['release']
                eol_time = item['eolTime']
                return {"eol_status": eol_status, "eol_release": eol_release, "eol_time": eol_time}, None
        return {"eol_status": "", "eol_release": "", "eol_time": ""}, None 
    except Exception as e:
        logger.error("eol_info error: {}".format(e))
        return {"eol_status": "", "eol_release": "", "eol_time": ""}, None

def criticality_score_checker(project_url: str, res_payload: dict, config: dict) -> None:
    """
    Criticality score checker
    
    Args:
        project_url: Project URL
        res_payload: Response payload
        config: Configuration dictionary
    """
    result, error = run_criticality_score(project_url, config)
    if error is None:
        logger.info(f"criticality-score job done: {project_url}")
        res_payload["scan_results"]["criticality-score"] = result
    else:
        logger.error(f"criticality-score job failed: {project_url}, error: {error}")
        res_payload["scan_results"]["criticality-score"] = {"error": error}


def scorecard_score_checker(project_url: str, res_payload: dict) -> None:
    """
    Scorecard score checker
    
    Args:
        project_url: Project URL
        res_payload: Response payload
    """
    result, error = run_scorecard_cli(project_url)
    if error is None:
        logger.info(f"scorecard-score job done: {project_url}")
        res_payload["scan_results"]["scorecard-score"] = result
    else:
        logger.error(f"scorecard-score job failed: {project_url}, error: {error}")
        res_payload["scan_results"]["scorecard-score"] = {"error": error}


def code_count_checker(project_url: str, res_payload: dict) -> None:
    """
    Code count checker
    
    Args:
        project_url: Project URL
        res_payload: Response payload
    """
    result, error = get_code_count(project_url)
    if error is None:
        logger.info(f"code-count job done: {project_url}")
        res_payload["scan_results"]["code-count"] = result
    else:
        logger.error(f"code-count job failed: {project_url}, error: {error}")
        res_payload["scan_results"]["code-count"] = {"error": error}


def package_info_checker(project_url: str, res_payload: dict) -> None:
    """
    Package info checker
    
    Args:
        project_url: Project URL
        res_payload: Response payload
    """
    result, error = get_package_info(project_url)
    if error is None:
        logger.info(f"package-info job done: {project_url}")
        res_payload["scan_results"]["package-info"] = result
    else:
        logger.error(f"package-info job failed: {project_url}, error: {error}")
        res_payload["scan_results"]["package-info"] = {"error": error}


def ohpm_info_checker(project_url: str, res_payload: dict) -> None:
    """
    OHPM info checker
    
    Args:
        project_url: Project URL
        res_payload: Response payload
    """
    result, error = get_ohpm_info(project_url)
    if error is None:
        logger.info(f"ohpm-info job done: {project_url}")
        res_payload["scan_results"]["ohpm-info"] = result
    else:
        logger.error(f"ohpm-info job failed: {project_url}, error: {error}")
        res_payload["scan_results"]["ohpm-info"] = {"error": error} 


def repo_country_organizations_checker(project_url: str, res_payload: dict) -> None:
    """
    Repository country/organization checker
    Args:
        project_url: Project URL
        res_payload: Response payload
    """ 
    res_payload["scan_results"]["repo-country-organizations"] = {}
    result_issue_country, error_issue_country = get_type_countries(project_url, 'issue_creators')
    if error_issue_country is None:
        logger.info(f"issue_country job done: {project_url}")
        res_payload["scan_results"]["repo-country-organizations"]["issue_creators_country"] = result_issue_country
    else:
        logger.error(f"issue_country job failed: {project_url}, error: {error_issue_country}")
        res_payload["scan_results"]["repo-country-organizations"]["issue_creators_country"] = {"error": error_issue_country}

    result_issue_org, error_issue_org = get_type_organizations(project_url, 'issue_creators')
    if error_issue_org is None:
        logger.info(f"issue_organizations job done: {project_url}")
        res_payload["scan_results"]["repo-country-organizations"]["issue_creators_organizations"] = result_issue_org
    else:
        logger.error(f"issue_organizations job failed: {project_url}, error: {error_issue_org}")
        res_payload["scan_results"]["repo-country-organizations"]["issue_creators_organizations"] = {"error": error_issue_org}

    result_pr_country, error_pr_country = get_type_countries(project_url, 'pull_request_creators')
    if error_pr_country is None:
        logger.info(f"pull_request_country job done: {project_url}")
        res_payload["scan_results"]["repo-country-organizations"]["pull_request_creators_country"] = result_pr_country
    else:
        logger.error(f"pull_request_country job failed: {project_url}, error: {error_pr_country}")
        res_payload["scan_results"]["repo-country-organizations"]["pull_request_creators_country"] = {"error": error_pr_country}

    result_pr_org, error_pr_org = get_type_organizations(project_url, 'pull_request_creators')
    if error_pr_org is None:
        logger.info(f"pull_request_organizations job done: {project_url}")
        res_payload["scan_results"]["repo-country-organizations"]["pull_request_creators_organizations"] = result_pr_org
    else:
        logger.error(f"pull_request_organizations job failed: {project_url}, error: {error_pr_org}")
        res_payload["scan_results"]["repo-country-organizations"]["pull_request_creators_organizations"] = {"error": error_pr_org}
    
    result_repo_country, error_repo_country = get_type_countries(project_url, 'stargazers')
    if error_repo_country is None:
        logger.info(f"stargazers_country job done: {project_url}")
        res_payload["scan_results"]["repo-country-organizations"]["stargazers_country"] = result_repo_country
    else:
        logger.error(f"stargazers_country job failed: {project_url}, error: {error_repo_country}")
        res_payload["scan_results"]["repo-country-organizations"]["stargazers_country"] = {"error": error_repo_country}

    result_repo_org, error_repo_org = get_type_organizations(project_url, 'stargazers')
    if error_repo_org is None:
        logger.info(f"stargazers_organizations job done: {project_url}")
        res_payload["scan_results"]["repo-country-organizations"]["stargazers_organizations"] = result_repo_org
    else:
        logger.error(f"stargazers_organizations job failed: {project_url}, error: {error_repo_org}")
        res_payload["scan_results"]["repo-country-organizations"]["stargazers_organizations"] = {"error": error_repo_org}
    
def eol_checker(project_url: str, res_payload: dict) -> None:
    """
    eol checker
    
    Args:
        project_url: Project URL
        res_payload: Response payload
    """
    result, error = get_eol_info(project_url)
    if error is None:
        logger.info(f"eol-checker job done: {project_url}")
        res_payload["scan_results"]["eol-checker"] = result
    else:
        logger.error(f"eol-checker job failed: {project_url}, error: {error}")
        res_payload["scan_results"]["eol-checker"] = {"error": error}
