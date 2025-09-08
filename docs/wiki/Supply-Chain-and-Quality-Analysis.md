# Supply Chain and Quality Analysis

> **Relevant source files**
> * [openchecker/checkers/standard_command_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py)
> * [openchecker/criticality/run.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/criticality/run.py)

This document covers the standard command checkers that analyze software supply chain health, quality metrics, and community characteristics. These checkers evaluate project criticality, package ecosystem data, code statistics, and contributor demographics to provide comprehensive supply chain risk assessment.

For security-focused analysis including dangerous workflows and webhook security, see [Security and Compliance Analysis](/Laniakea2012/openchecker/4.3-security-and-compliance-analysis). For Software Bill of Materials (SBOM) detection and analysis, see [SBOM Analysis](/Laniakea2012/openchecker/4.5-sbom-analysis).

## Overview

The supply chain and quality analysis system consists of multiple specialized checkers that evaluate different aspects of software projects:

```mermaid
flowchart TD

Agent["openchecker-agent"]
Dispatcher["_execute_commands"]
CriticalityChecker["criticality_score_checker"]
ScorecardChecker["scorecard_score_checker"]
CodeCountChecker["code_count_checker"]
PackageChecker["package_info_checker"]
OHPMChecker["ohpm_info_checker"]
CommunityChecker["repo_country_organizations_checker"]
CriticalityTool["criticality_score CLI"]
ScorecardTool["scorecard CLI"]
ClocTool["cloc CLI"]
NPMRegistry["npm registry API"]
PlatformAdapter["platform_manager"]
OHPMRegistry["OHPM registry API"]
OHPMConfig["ohpm_repo.json"]
OSSInsight["OSSInsight API"]
ResultPayload["res_payload['scan_results']"]

Agent --> Dispatcher
Dispatcher --> CriticalityChecker
Dispatcher --> ScorecardChecker
Dispatcher --> CodeCountChecker
Dispatcher --> PackageChecker
Dispatcher --> OHPMChecker
Dispatcher --> CommunityChecker
CriticalityChecker --> CriticalityTool
ScorecardChecker --> ScorecardTool
CodeCountChecker --> ClocTool
PackageChecker --> NPMRegistry
PackageChecker --> PlatformAdapter
OHPMChecker --> OHPMRegistry
OHPMChecker --> OHPMConfig
CommunityChecker --> OSSInsight
CriticalityChecker --> ResultPayload
ScorecardChecker --> ResultPayload
CodeCountChecker --> ResultPayload
PackageChecker --> ResultPayload
OHPMChecker --> ResultPayload
CommunityChecker --> ResultPayload
```

Sources: [openchecker/checkers/standard_command_checker.py L300-L440](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L300-L440)

## Criticality Score Analysis

The criticality score assessment evaluates project importance based on multiple metrics including community activity, dependency usage, and maintenance indicators.

### Criticality Score Checker

The `criticality_score_checker` function integrates with the Google OSS criticality score tool to assess project importance:

```mermaid
sequenceDiagram
  participant openchecker-agent
  participant criticality_score_checker
  participant criticality_score CLI
  participant GitHub API

  openchecker-agent->>criticality_score_checker: "criticality_score_checker(project_url, res_payload, config)"
  criticality_score_checker->>criticality_score_checker: "run_criticality_score(project_url, config)"
  loop ["GitHub project"]
    criticality_score_checker->>criticality_score CLI: "criticality_score --repo <url> --format json"
    note over criticality_score CLI: "Uses GITHUB_AUTH_TOKEN from config"
    criticality_score CLI->>GitHub API: "API calls for repository metrics"
    GitHub API-->>criticality_score CLI: "Repository statistics"
    criticality_score CLI-->>criticality_score_checker: "JSON criticality score result"
    criticality_score_checker->>criticality_score_checker: "Parse JSON from stderr output"
    criticality_score_checker-->>openchecker-agent: "error: URL not supported"
  end
  criticality_score_checker-->>openchecker-agent: "Update res_payload['scan_results']['criticality-score']"
```

The criticality score calculation considers multiple repository metrics:

| Metric | Weight | Description |
| --- | --- | --- |
| `created_since` | Time-based | Months since repository creation |
| `updated_since` | Time-based | Months since last commit |
| `contributor_count` | Community | Number of unique contributors |
| `org_count` | Diversity | Number of different organizations |
| `commit_frequency` | Activity | Average commits per week |
| `recent_releases_count` | Maintenance | Recent releases in lookback period |
| `updated_issues_count` | Engagement | Issues updated recently |
| `closed_issues_count` | Responsiveness | Issues closed recently |
| `comment_frequency` | Communication | Average comments per issue |
| `dependents_count` | Usage | Number of dependent projects |

Sources: [openchecker/checkers/standard_command_checker.py L13-L49](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L13-L49)

 [openchecker/criticality/run.py L51-L55](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/criticality/run.py#L51-L55)

 [openchecker/criticality/run.py L479-L532](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/criticality/run.py#L479-L532)

### Scorecard Integration

The `scorecard_score_checker` leverages the OSSF Scorecard project to evaluate security and maintenance practices:

```mermaid
flowchart TD

ScorecardChecker["scorecard_score_checker"]
ScorecardCLI["scorecard --repo  --format json"]
ScorecardResult["Raw scorecard JSON"]
Simplifier["simplify_scorecard()"]
SimplifiedResult["{'score': float, 'checks': [{'name': str, 'score': int}]}"]
ResultPayload["res_payload['scan_results']['scorecard-score']"]

ScorecardChecker --> ScorecardCLI
ScorecardCLI --> ScorecardResult
ScorecardResult --> Simplifier
Simplifier --> SimplifiedResult
SimplifiedResult --> ResultPayload
```

The scorecard results are simplified to include only essential metrics, filtering out detailed documentation and focusing on scores for each security check.

Sources: [openchecker/checkers/standard_command_checker.py L51-L101](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L51-L101)

 [openchecker/checkers/standard_command_checker.py L318-L332](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L318-L332)

## Package and Registry Analysis

The system analyzes package ecosystem data from multiple registry sources to assess supply chain characteristics.

### NPM Package Analysis

The `package_info_checker` retrieves comprehensive package metadata from the npm registry:

```mermaid
flowchart TD

PackageChecker["package_info_checker"]
GetPackageInfo["get_package_info()"]
ExtractName["Extract package name from URL"]
NPMQuery["GET Unsupported markdown: link"]
NPMSuccess["Status 200"]
NPMFail["Status != 200"]
ParseMetadata["Parse package metadata"]
DownloadStats["GET Unsupported markdown: link"]
CombineData["Combine metadata + download stats"]
PlatformFallback["platform_manager.get_repo_info()"]
PlatformDownloads["platform_manager.get_download_stats()"]
ResultStructure["{'description': str, 'home_url': str, 'dependent_count': int, 'down_count': int, 'day_enter': str}"]
FinalResult["res_payload['scan_results']['package-info']"]

PackageChecker --> GetPackageInfo
GetPackageInfo --> ExtractName
ExtractName --> NPMQuery
NPMQuery --> NPMSuccess
NPMQuery --> NPMFail
NPMSuccess --> ParseMetadata
ParseMetadata --> DownloadStats
DownloadStats --> CombineData
NPMFail --> PlatformFallback
PlatformFallback --> PlatformDownloads
CombineData --> ResultStructure
PlatformDownloads --> ResultStructure
ResultStructure --> FinalResult
```

Sources: [openchecker/checkers/standard_command_checker.py L130-L196](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L130-L196)

 [openchecker/checkers/standard_command_checker.py L352-L366](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L352-L366)

### OHPM Package Analysis

For OpenHarmony projects, the `ohpm_info_checker` analyzes OHPM registry data:

```mermaid
sequenceDiagram
  participant ohpm_info_checker
  participant config/ohpm_repo.json
  participant OHPM Registry API

  ohpm_info_checker->>config/ohpm_repo.json: "Load ohpm_repo.json mapping"
  ohpm_info_checker->>ohpm_info_checker: "Match project_url to package name"
  loop ["Package found in mapping"]
    ohpm_info_checker->>OHPM Registry API: "GET https://ohpm.openharmony.cn/ohpmweb/registry/oh-package/openapi/v1/detail/{name}"
    OHPM Registry API-->>ohpm_info_checker: "Package details JSON"
    ohpm_info_checker->>ohpm_info_checker: "Extract downloads, dependencies, dependents"
    ohpm_info_checker-->>ohpm_info_checker: "Return empty values"
  end
  ohpm_info_checker-->>ohpm_info_checker: "Update res_payload with OHPM statistics"
```

The OHPM analysis extracts three key metrics:

* `down_count`: Total download count
* `dependent`: Number of packages this package depends on
* `bedependent`: Number of packages that depend on this package

Sources: [openchecker/checkers/standard_command_checker.py L198-L232](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L198-L232)

 [openchecker/checkers/standard_command_checker.py L369-L383](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L369-L383)

## Code Quality Metrics

### Code Count Analysis

The `code_count_checker` uses the `cloc` tool to analyze codebase size and composition:

```mermaid
flowchart TD

CodeChecker["code_count_checker"]
GetCodeCount["get_code_count()"]
CloneCheck["Check if project exists locally"]
GitClone["git clone --depth=1 if needed"]
ClocExecution["cloc  --json"]
ParseJSON["Parse cloc JSON output"]
ExtractCount["Extract result_json['SUM']['code']"]
ResultPayload["res_payload['scan_results']['code-count']"]

CodeChecker --> GetCodeCount
GetCodeCount --> CloneCheck
CloneCheck --> GitClone
GitClone --> ClocExecution
ClocExecution --> ParseJSON
ParseJSON --> ExtractCount
ExtractCount --> ResultPayload
```

The code count analysis provides the total lines of code across all files in the repository, giving an indication of project size and complexity.

Sources: [openchecker/checkers/standard_command_checker.py L104-L127](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L104-L127)

 [openchecker/checkers/standard_command_checker.py L335-L349](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L335-L349)

## Community and Geographic Analysis

The system analyzes contributor demographics and geographic distribution using the OSSInsight API.

### Geographic and Organizational Distribution

The `repo_country_organizations_checker` collects comprehensive community analysis data:

```mermaid
flowchart TD

CommunityChecker["repo_country_organizations_checker"]
IssueCountries["get_type_countries(url, 'issue_creators')"]
IssueOrgs["get_type_organizations(url, 'issue_creators')"]
PRCountries["get_type_countries(url, 'pull_request_creators')"]
PROrgs["get_type_organizations(url, 'pull_request_creators')"]
StarCountries["get_type_countries(url, 'stargazers')"]
StarOrgs["get_type_organizations(url, 'stargazers')"]
OSSInsightAPI1["api.ossinsight.io/v1/repos/{owner}/{repo}/issue_creators/countries/"]
OSSInsightAPI2["api.ossinsight.io/v1/repos/{owner}/{repo}/issue_creators/organizations/"]
OSSInsightAPI3["api.ossinsight.io/v1/repos/{owner}/{repo}/pull_request_creators/countries/"]
OSSInsightAPI4["api.ossinsight.io/v1/repos/{owner}/{repo}/pull_request_creators/organizations/"]
OSSInsightAPI5["api.ossinsight.io/v1/repos/{owner}/{repo}/stargazers/countries/"]
OSSInsightAPI6["api.ossinsight.io/v1/repos/{owner}/{repo}/stargazers/organizations/"]
Results["Multiple result fields in res_payload"]

CommunityChecker --> IssueCountries
CommunityChecker --> IssueOrgs
CommunityChecker --> PRCountries
CommunityChecker --> PROrgs
CommunityChecker --> StarCountries
CommunityChecker --> StarOrgs
IssueCountries --> OSSInsightAPI1
IssueOrgs --> OSSInsightAPI2
PRCountries --> OSSInsightAPI3
PROrgs --> OSSInsightAPI4
StarCountries --> OSSInsightAPI5
StarOrgs --> OSSInsightAPI6
OSSInsightAPI1 --> Results
OSSInsightAPI2 --> Results
OSSInsightAPI3 --> Results
OSSInsightAPI4 --> Results
OSSInsightAPI5 --> Results
OSSInsightAPI6 --> Results
```

The community analysis generates six distinct result fields:

* `issue_creators_country`: Geographic distribution of issue creators
* `issue_creators_organizations`: Organizational distribution of issue creators
* `pull_request_creators_country`: Geographic distribution of PR creators
* `pull_request_creators_organizations`: Organizational distribution of PR creators
* `stargazers_country`: Geographic distribution of stargazers
* `stargazers_organizations`: Organizational distribution of stargazers

Sources: [openchecker/checkers/standard_command_checker.py L234-L296](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L234-L296)

 [openchecker/checkers/standard_command_checker.py L386-L439](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L386-L439)

## Integration with Analysis Workflow

These checkers integrate into the broader OpenChecker analysis pipeline through the command execution framework:

```mermaid
sequenceDiagram
  participant openchecker-agent
  participant _execute_commands
  participant Standard Command Checker
  participant External Service/Tool

  openchecker-agent->>_execute_commands: "Process analysis task"
  _execute_commands->>_execute_commands: "Parse command_list for standard checkers"
  loop ["For each standard command"]
    _execute_commands->>Standard Command Checker: "Call checker function"
    Standard Command Checker->>External Service/Tool: "Execute external tool/API call"
    External Service/Tool-->>Standard Command Checker: "Return analysis results"
    Standard Command Checker->>Standard Command Checker: "Process and format results"
    Standard Command Checker-->>_execute_commands: "Update res_payload['scan_results'][<checker_name>]"
  end
  _execute_commands-->>openchecker-agent: "Return completed res_payload"
```

Each checker follows a consistent pattern:

1. Receives `project_url`, `res_payload`, and optional `config` parameters
2. Executes analysis using external tools or API calls
3. Processes results into standardized format
4. Updates the `res_payload['scan_results']` dictionary with results or error information
5. Logs success or failure messages

Sources: [openchecker/checkers/standard_command_checker.py L300-L440](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/standard_command_checker.py#L300-L440)