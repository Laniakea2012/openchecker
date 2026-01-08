import os
import json
import time
import re
import requests
from typing import Dict, Tuple
from constans import shell_script_handlers
from common import shell_exec
from platform_adapter import platform_manager
from logger import get_logger

logger = get_logger('openchecker.checkers.sonar_checker')


def _build_sonar_url(sonar_config: dict, path: str) -> str:
    """
    Build SonarQube API URL
    Matches the logic in shell script (constans.py):
    - If host already contains protocol (http:// or https://), use it directly
    - If host is an IP address, use http://IP:port
    - If host is a domain name, use https://domain (443 is default HTTPS port)
    
    Args:
        sonar_config: SonarQube configuration
        path: API path (e.g., '/api/projects/create')
    
    Returns:
        Complete URL
    """
    host = sonar_config.get('host', 'localhost')
    port = sonar_config.get('port', '9000')
    
    # Check if host already contains protocol
    if host.startswith('http://') or host.startswith('https://'):
        # Host already has protocol, use it directly
        base_url = host
    else:
        # Check if it's an IP address
        ip_pattern = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')
        if ip_pattern.match(host):
            # It's an IP address, use http protocol and add port
            if port and str(port) != 'None':
                base_url = f"http://{host}:{port}"
            else:
                base_url = f"http://{host}"
        else:
            # It's a domain name, use https protocol
            # For standard HTTPS port 443, no need to add port explicitly
            if str(port) == '443':
                base_url = f"https://{host}"
            else:
                base_url = f"https://{host}:{port}"
    
    # Ensure path starts with /
    if not path.startswith('/'):
        path = f"/{path}"
    
    return f"{base_url}{path}"


def sonar_checker(project_url: str, res_payload: dict, config: dict) -> None:
    """
    SonarQube scanner checker
    
    Args:
        project_url: Project URL
        res_payload: Response payload
        config: Configuration dictionary
    """
    try:
        # Use platform adapter to parse project URL
        try:
            owner_name, repo_name = platform_manager.parse_project_url(project_url)
            adapter = platform_manager.get_adapter(project_url)
            platform = adapter.get_platform_name() if adapter else "other"
            organization = owner_name
            project = repo_name
        except ValueError:
            platform, organization, project = "other", "default", "default"
        
        sonar_project_name = f"{platform}_{organization}_{project}".lower()
        sonar_config = config.get("SonarQube", {})
        
        if not _check_sonar_project_exists(sonar_project_name, sonar_config):
            _create_sonar_project(sonar_project_name, sonar_config)
        
        shell_script = shell_script_handlers["sonar-scanner"].format(
            project_url=project_url, 
            sonar_project_name=sonar_project_name, 
            sonar_host=sonar_config.get('host', 'localhost'),
            sonar_port=sonar_config.get('port', '9000'),
            sonar_token=sonar_config.get('token', ''),
            scan_timeout_s=sonar_config.get('scan_timeout_s', '1800')
        )
        result, error = shell_exec(shell_script)
        
        if error is None:
            logger.info(f"sonar-scanner finish scanning project: {project_url}, report querying...")
            logger.info(f"SonarQube project name: {sonar_project_name}")
            logger.info(f"SonarQube dashboard URL: http://{sonar_config['host']}:{sonar_config['port']}/dashboard?id={sonar_project_name}")
            
            sonar_result = _query_sonar_measures(sonar_project_name, sonar_config)
            
            # 检查是否有度量数据
            if sonar_result.get("component", {}).get("measures"):
                logger.info(f"sonar-scanner job done with {len(sonar_result['component']['measures'])} metrics: {project_url}")
                res_payload["scan_results"]["sonar-scanner"] = sonar_result
            else:
                logger.warning(f"sonar-scanner completed but no metrics found: {project_url}")
                logger.warning(f"Check SonarQube dashboard: http://{sonar_config['host']}:{sonar_config['port']}/dashboard?id={sonar_project_name}")
                
                # 提供更详细的诊断信息
                diagnostic_info = {
                    "status": "no_metrics",
                    "project_key": sonar_project_name,
                    "dashboard_url": f"http://{sonar_config['host']}:{sonar_config['port']}/dashboard?id={sonar_project_name}",
                    "possible_causes": [
                        "Maven compilation may have failed silently",
                        "No source files were found to analyze",
                        "Java bytecode files (*.class) were not generated",
                        "SonarQube quality gate configuration issue",
                        "Multi-module project structure not properly handled"
                    ],
                    "suggestions": [
                        "Check if 'mvn clean install' succeeded",
                        "Verify target/classes directories exist",
                        "Check SonarQube server logs",
                        "Try running 'mvn sonar:sonar' manually with -X flag"
                    ]
                }
                
                if sonar_result.get("analysis_error"):
                    diagnostic_info["analysis_error"] = sonar_result["analysis_error"]
                
                res_payload["scan_results"]["sonar-scanner"] = {**sonar_result, **diagnostic_info}
        else:
            logger.error(f"sonar-scanner job failed: {project_url}, error: {error}")
            res_payload["scan_results"]["sonar-scanner"] = {"error": error.decode("utf-8")}
            
    except Exception as e:
        logger.error(f"sonar-scanner job failed: {project_url}, error: {e}")
        res_payload["scan_results"]["sonar-scanner"] = {"error": str(e)}


def _check_sonar_project_exists(project_name: str, sonar_config: dict) -> bool:
    """
    Check if SonarQube project already exists
    
    Args:
        project_name: Project name
        sonar_config: SonarQube configuration
        
    Returns:
        bool: Whether project exists
    """
    try:
        search_api_url = _build_sonar_url(sonar_config, '/api/projects/search')
        auth = (sonar_config.get("username"), sonar_config.get("password"))
        
        response = requests.get(
            search_api_url, 
            auth=auth, 
            params={"projects": project_name},
            timeout=30
        )

        if response.status_code == 200:
            logger.info("Call sonarqube projects search api success: 200")
            result = json.loads(response.text)
            exists = result["paging"]["total"] > 0
            if exists:
                logger.info(f"SonarQube project {project_name} already exists")
            return exists
        else:
            logger.error(f"Call sonarqube projects search api failed with status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Call sonarqube projects search api failed with error: {e}")
        return False
    except Exception as e:
        logger.error(f"Exception checking SonarQube project: {e}")
        return False


def _create_sonar_project(project_name: str, sonar_config: dict) -> None:
    """
    Create SonarQube project
    
    Args:
        project_name: Project name
        sonar_config: SonarQube configuration
    """
    try:
        create_api_url = _build_sonar_url(sonar_config, '/api/projects/create')
        auth = (sonar_config.get("username"), sonar_config.get("password"))
        
        payload = {
            "project": project_name, 
            "name": project_name
        }
        
        response = requests.post(create_api_url, auth=auth, data=payload, timeout=60)
        if response.status_code == 200:
            logger.info("Call sonarqube projects create api success: 200")
            logger.info(f"SonarQube project {project_name} created successfully")
        else:
            logger.error(f"Call sonarqube projects create api failed with status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Call sonarqube projects create api failed with error: {e}")
    except Exception as e:
        logger.error(f"Exception creating SonarQube project: {e}")


def _get_analysis_logs(project_name: str, sonar_config: dict) -> dict:
    """
    Get analysis task logs to diagnose issues
    
    Args:
        project_name: Project name
        sonar_config: SonarQube configuration
        
    Returns:
        dict: Analysis task information
    """
    try:
        logger.info(f"Querying analysis task history for project: {project_name}")
        ce_activity_url = f"http://{sonar_config['host']}:{sonar_config['port']}/api/ce/activity"
        auth = (sonar_config.get("username"), sonar_config.get("password"))
        
        response = requests.get(
            ce_activity_url,
            auth=auth,
            params={"component": project_name, "ps": 5},  # 获取最近5个任务
            timeout=30
        )
        
        logger.info(f"CE activity API response status: {response.status_code}")
        
        if response.status_code == 200:
            activity_data = json.loads(response.text)
            tasks = activity_data.get("tasks", [])
            
            logger.info(f"Found {len(tasks)} analysis tasks in history")
            
            if tasks:
                # 显示所有任务的状态
                for i, task in enumerate(tasks[:3]):
                    logger.info(f"Task {i+1}: status={task.get('status')}, type={task.get('type')}, submittedAt={task.get('submittedAt')}")
                
                latest_task = tasks[0]
                task_id = latest_task.get("id")
                status = latest_task.get("status")
                task_type = latest_task.get("type")
                
                logger.info(f"Latest analysis task: id={task_id}, status={status}, type={task_type}")
                
                # 如果任务失败，获取错误信息
                if status == "FAILED":
                    error_msg = latest_task.get("errorMessage", "No error message available")
                    logger.error(f"Analysis FAILED with error: {error_msg}")
                    return {"status": status, "error": error_msg, "task": latest_task}
                elif status == "SUCCESS":
                    # 即使成功也可能没有生成度量数据
                    warnings = latest_task.get("warnings", [])
                    analysis_time_ms = latest_task.get("executionTimeMs", 0)
                    logger.info(f"Analysis task succeeded in {analysis_time_ms}ms")
                    
                    if warnings:
                        logger.warning(f"⚠️  Analysis succeeded with {len(warnings)} warnings: {warnings}")
                    
                    # 检查任务详情以获取更多信息
                    has_errors_or_warnings = latest_task.get("hasErrorsOrWarnings", False)
                    if has_errors_or_warnings:
                        logger.warning("Task has errors or warnings flag set")
                    
                    return {"status": status, "warnings": warnings, "execution_time_ms": analysis_time_ms, "task": latest_task}
                else:
                    logger.warning(f"Unexpected task status: {status}")
                    return {"status": status, "task": latest_task}
            else:
                logger.warning("No analysis tasks found in history")
                return {"error": "No analysis tasks found"}
        else:
            logger.error(f"Failed to query CE activity: HTTP {response.status_code}")
            return {"error": f"HTTP {response.status_code}"}
        
    except Exception as e:
        logger.error(f"Exception while getting analysis logs: {e}", exc_info=True)
        return {"error": str(e)}


def _query_sonar_measures(project_name: str, sonar_config: dict) -> dict:
    """
    Query SonarQube project metrics
    
    Args:
        project_name: Project name
        sonar_config: SonarQube configuration
        
    Returns:
        dict: Query result
    """
    try:
        logger.info("Waiting for SonarQube background task processing...")
        
        # 从配置文件读取等待时间和检查间隔
        report_max_wait_time_s = int(sonar_config.get("report_max_wait_time_s", 120))
        report_check_interval_s = int(sonar_config.get("report_check_interval_s", 10))
        elapsed_time = 0
        
        ce_task_url = _build_sonar_url(sonar_config, '/api/ce/component')
        auth = (sonar_config.get("username"), sonar_config.get("password"))
        
        while elapsed_time < report_max_wait_time_s:
            time.sleep(report_check_interval_s)
            elapsed_time += report_check_interval_s
            
            try:
                response = requests.get(
                    ce_task_url, 
                    auth=auth, 
                    params={"component": project_name},
                    timeout=30
                )
                
                if response.status_code == 200:
                    task_data = json.loads(response.text)
                    if task_data.get("queue", []):
                        logger.info(f"Background tasks still in queue, waiting... ({elapsed_time}s)")
                        continue
                    
                    current_task = task_data.get("current")
                    if current_task and current_task.get("status") == "IN_PROGRESS":
                        logger.info(f"Background task in progress, waiting... ({elapsed_time}s)")
                        continue
                    
                    # 任务完成
                    logger.info("Background task completed")
                    break
                else:
                    logger.warning(f"Could not check task status: {response.status_code}, proceeding anyway...")
                    break
                    
            except Exception as e:
                logger.warning(f"Error checking task status: {e}, proceeding anyway...")
                break
        
        # 额外等待10秒确保数据完全可用
        time.sleep(10)
        
        measures_api_url = _build_sonar_url(sonar_config, '/api/measures/component')
        
        params = {
            "component": project_name, 
            "metricKeys": "coverage,complexity,duplicated_lines_density,lines,reliability_rating,sqale_rating,security_rating,security_review_rating"
        }
        
        response = requests.get(measures_api_url, auth=auth, params=params, timeout=30)
        
        if response.status_code == 200:
            logger.info("Querying sonar-scanner report success: 200")
            result = json.loads(response.text)
            
            # 如果没有度量数据，记录警告并查询分析日志
            if not result.get("component", {}).get("measures"):
                logger.warning(f"No measures data found for project: {project_name}")
                logger.warning("This may indicate the analysis did not complete successfully")
                
                # 查询最近的分析任务详情
                analysis_log = _get_analysis_logs(project_name, sonar_config)
                if analysis_log:
                    logger.error(f"Analysis task details: {analysis_log}")
                    result["analysis_error"] = analysis_log
            
            return result
        else:
            logger.error(f"Querying sonar-scanner report failed with status code: {response.status_code}")
            return {"error": f"Query failed with status code: {response.status_code}"}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Querying sonar-scanner report failed with error: {e}")
        return {"error": f"Query failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Exception querying SonarQube measures: {e}")
        return {"error": f"Query exception: {str(e)}"} 