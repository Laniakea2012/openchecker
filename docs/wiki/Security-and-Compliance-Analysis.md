# Security and Compliance Analysis

> **Relevant source files**
> * [openchecker/checkers/binary_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/binary_checker.py)
> * [openchecker/checkers/changed_files_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/changed_files_checker.py)
> * [openchecker/checkers/document_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py)
> * [openchecker/checkers/release_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/release_checker.py)
> * [openchecker/checkers/sonar_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py)
> * [openchecker/checkers/url_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/url_checker.py)

This document covers OpenChecker's security and compliance analysis capabilities, which include binary file detection, code quality analysis, document compliance checking, release security validation, and file change monitoring. The security analysis system consists of specialized checkers that examine repositories for potential security risks, compliance violations, and adherence to software development best practices.

For information about SBOM analysis tools, see [4.5](/Laniakea2012/openchecker/4.5-sbom-analysis). For platform-specific integrations that these security checkers depend on, see [5.1](/Laniakea2012/openchecker/5.1-version-control-platform-adapters).

## Security Checker Architecture

The security analysis system consists of six main checkers that examine different aspects of repository security and compliance. All checkers follow a consistent pattern with standardized function signatures and shared utility dependencies.

### Security and Compliance Checker Components

```mermaid
flowchart TD

CommonShell["common.py<br>shell_exec()"]
PlatformMgr["platform_adapter<br>platform_manager"]
Logger["logger<br>get_logger()"]
ExponentialBackoff["exponential_backoff<br>completion_with_backoff()"]
BinaryChecker["binary_checker.py<br>binary_checker()"]
ChangedFiles["changed_files_checker.py<br>changed_files_detector()"]
URLChecker["url_checker.py<br>url_checker()"]
ShellScript["scripts/binary_checker.sh"]
GitDiff["_get_diff_files()"]
SonarChecker["sonar_checker.py<br>sonar_checker()"]
SonarProject["_check_sonar_project_exists()"]
SonarCreate["_create_sonar_project()"]
SonarQuery["_query_sonar_measures()"]
DocumentChecker["document_checker.py<br>check_doc_content()"]
ReadmeChecker["check_readme_opensource()"]
APIDocChecker["api_doc_checker()"]
BuildDocChecker["build_doc_checker()"]
ReadmeOpenSourceChecker["readme_opensource_checker()"]
ReleaseChecker["release_checker.py<br>release_checker()"]
ReleaseContents["check_release_contents()"]
SignedRelease["check_signed_release()"]
GetReleases["get_all_releases_with_assets()"]

BinaryChecker --> CommonShell
ChangedFiles --> Logger
URLChecker --> Logger
SonarChecker --> PlatformMgr
SonarChecker --> CommonShell
DocumentChecker --> ExponentialBackoff
DocumentChecker --> Logger
ReleaseChecker --> PlatformMgr

subgraph subGraph4 ["Release Security"]
    ReleaseChecker
    ReleaseContents
    SignedRelease
    GetReleases
    ReleaseChecker --> ReleaseContents
    ReleaseChecker --> SignedRelease
    ReleaseChecker --> GetReleases
end

subgraph subGraph3 ["Document Compliance"]
    DocumentChecker
    ReadmeChecker
    APIDocChecker
    BuildDocChecker
    ReadmeOpenSourceChecker
    APIDocChecker --> DocumentChecker
    BuildDocChecker --> DocumentChecker
    ReadmeOpenSourceChecker --> ReadmeChecker
end

subgraph subGraph2 ["Code Quality and Security"]
    SonarChecker
    SonarProject
    SonarCreate
    SonarQuery
    SonarChecker --> SonarProject
    SonarChecker --> SonarCreate
    SonarChecker --> SonarQuery
end

subgraph subGraph1 ["File and Binary Security"]
    BinaryChecker
    ChangedFiles
    URLChecker
    ShellScript
    GitDiff
    BinaryChecker --> ShellScript
    ChangedFiles --> GitDiff
end

subgraph subGraph0 ["Core Infrastructure"]
    CommonShell
    PlatformMgr
    Logger
    ExponentialBackoff
end
```

**Sources:** [openchecker/checkers/binary_checker.py L1-L42](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/binary_checker.py#L1-L42)

 [openchecker/checkers/changed_files_checker.py L1-L77](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/changed_files_checker.py#L1-L77)

 [openchecker/checkers/url_checker.py L1-L25](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/url_checker.py#L1-L25)

 [openchecker/checkers/sonar_checker.py L1-L173](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py#L1-L173)

 [openchecker/checkers/document_checker.py L1-L200](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py#L1-L200)

 [openchecker/checkers/release_checker.py L1-L282](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/release_checker.py#L1-L282)

## Binary and File Security Analysis

The binary and file security analysis system detects potentially dangerous files and monitors changes that could introduce security risks.

### Binary File Detection

The `binary_checker` identifies binary files and archives that may pose security risks or violate open source compliance requirements.

```mermaid
flowchart TD

ProjectURL["project_url"]
ShellScript["scripts/binary_checker.sh"]
ShellExec["shell_exec()"]
ProcessOutput["Process Script Output"]
OutputParsing["result.decode('utf-8')"]
SplitLines["data_list = result_str.split('<br>')"]
BinaryFiles["'Binary file found:' pattern"]
BinaryArchives["'Binary archive found:' pattern"]
BinaryFileList["binary_file_list[]"]
BinaryArchiveList["binary_archive_list[]"]
FinalResult["{'binary_file_list': [], 'binary_archive_list': []}"]
ScanResults["res_payload['scan_results']['binary-checker']"]

ProcessOutput --> OutputParsing
BinaryFiles --> BinaryFileList
BinaryArchives --> BinaryArchiveList

subgraph subGraph2 ["Results Structure"]
    BinaryFileList
    BinaryArchiveList
    FinalResult
    ScanResults
    BinaryFileList --> FinalResult
    BinaryArchiveList --> FinalResult
    FinalResult --> ScanResults
end

subgraph subGraph1 ["File Classification"]
    OutputParsing
    SplitLines
    BinaryFiles
    BinaryArchives
    OutputParsing --> SplitLines
    SplitLines --> BinaryFiles
    SplitLines --> BinaryArchives
end

subgraph subGraph0 ["Binary Detection Pipeline"]
    ProjectURL
    ShellScript
    ShellExec
    ProcessOutput
    ProjectURL --> ShellScript
    ShellScript --> ShellExec
    ShellExec --> ProcessOutput
end
```

**Sources:** [openchecker/checkers/binary_checker.py L9-L42](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/binary_checker.py#L9-L42)

 [openchecker/checkers/binary_checker.py L18-L21](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/binary_checker.py#L18-L21)

 [openchecker/checkers/binary_checker.py L25-L36](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/binary_checker.py#L25-L36)

### File Change Security Analysis

The `changed_files_detector` monitors repository changes to identify potentially risky modifications between commits.

```mermaid
flowchart TD

ProjectURL["project_url"]
CommitHash["commit_hash parameter"]
ParseURL["urlparse(project_url).path"]
RepositoryPath["os.path.join(context_path, repo_name)"]
ChangeDirectory["os.chdir(repository_path)"]
GetDiffFiles["_get_diff_files()"]
GitDiffCommand["git diff --name-only --diff-filter={type} {commit_hash}..HEAD"]
DiffTypes["ACDMRTUXB - All changes<br>A - Added<br>R - Renamed<br>D - Deleted<br>M - Modified"]
ChangedFiles["changed_files = _get_diff_files(commit_hash, 'ACDMRTUXB')"]
NewFiles["new_files = _get_diff_files(commit_hash, 'A')"]
RenameFiles["rename_files = _get_diff_files(commit_hash, 'R')"]
DeletedFiles["deleted_files = _get_diff_files(commit_hash, 'D')"]
ModifiedFiles["modified_files = _get_diff_files(commit_hash, 'M')"]
ScanResults["res_payload['scan_results']['changed-files-since-commit-detector']"]
ResultStructure["{'changed_files': [], 'new_files': [],<br>'rename_files': [], 'deleted_files': [], 'modified_files': []}"]

ChangeDirectory --> GetDiffFiles
DiffTypes --> ChangedFiles
DiffTypes --> NewFiles
DiffTypes --> RenameFiles
DiffTypes --> DeletedFiles
DiffTypes --> ModifiedFiles
ChangedFiles --> ResultStructure
NewFiles --> ResultStructure
RenameFiles --> ResultStructure
DeletedFiles --> ResultStructure
ModifiedFiles --> ResultStructure

subgraph subGraph3 ["Results Output"]
    ScanResults
    ResultStructure
    ResultStructure --> ScanResults
end

subgraph subGraph2 ["Change Classification"]
    ChangedFiles
    NewFiles
    RenameFiles
    DeletedFiles
    ModifiedFiles
end

subgraph subGraph1 ["Git Diff Analysis"]
    GetDiffFiles
    GitDiffCommand
    DiffTypes
    GetDiffFiles --> GitDiffCommand
    GitDiffCommand --> DiffTypes
end

subgraph subGraph0 ["Git Analysis Setup"]
    ProjectURL
    CommitHash
    ParseURL
    RepositoryPath
    ChangeDirectory
    ProjectURL --> ParseURL
    ParseURL --> RepositoryPath
    CommitHash --> ChangeDirectory
    RepositoryPath --> ChangeDirectory
end
```

**Sources:** [openchecker/checkers/changed_files_checker.py L10-L52](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/changed_files_checker.py#L10-L52)

 [openchecker/checkers/changed_files_checker.py L54-L77](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/changed_files_checker.py#L54-L77)

 [openchecker/checkers/changed_files_checker.py L34-L49](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/changed_files_checker.py#L34-L49)

### URL Security Validation

The `url_checker` validates URL accessibility and security for project links.

```mermaid
flowchart TD

ProjectURL["project_url"]
HTTPRequest["requests.get(project_url, timeout=10)"]
StatusCheck["response.status_code"]
AccessibilityCheck["is_accessible = (status_code == 200)"]
SuccessResult["{'status_code': code, 'is_accessible': boolean}"]
ErrorResult["{'error': str(exception)}"]
ScanResults["res_payload['scan_results']['url-checker']"]

AccessibilityCheck --> SuccessResult
HTTPRequest --> ErrorResult

subgraph subGraph1 ["Security Results"]
    SuccessResult
    ErrorResult
    ScanResults
    SuccessResult --> ScanResults
    ErrorResult --> ScanResults
end

subgraph subGraph0 ["URL Validation Process"]
    ProjectURL
    HTTPRequest
    StatusCheck
    AccessibilityCheck
    ProjectURL --> HTTPRequest
    HTTPRequest --> StatusCheck
    StatusCheck --> AccessibilityCheck
end
```

**Sources:** [openchecker/checkers/url_checker.py L8-L25](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/url_checker.py#L8-L25)

 [openchecker/checkers/url_checker.py L16-L21](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/url_checker.py#L16-L21)

## Code Quality and Security Analysis

### SonarQube Integration

The `sonar_checker` integrates with SonarQube server to perform comprehensive code quality and security analysis.

```mermaid
flowchart TD

ProjectURL["project_url"]
PlatformManager["platform_manager.parse_project_url()"]
ProjectNaming["sonar_project_name = f'{platform}{organization}{project}'"]
ProjectExists["_check_sonar_project_exists()"]
CreateProject["_create_sonar_project()"]
ShellScriptFormat["shell_script_handlers['sonar-scanner'].format()"]
SonarScanExec["shell_exec(shell_script)"]
ScanParameters["project_url, sonar_project_name,<br>sonar_host, sonar_port, sonar_token"]
WaitProcessing["time.sleep(30) # Wait for processing"]
QueryMeasures["_query_sonar_measures()"]
MeasuresAPI["/api/measures/component"]
MetricKeys["'coverage,complexity,duplicated_lines_density,lines'"]
SearchAPI["/api/projects/search"]
CreateAPI["/api/projects/create"]
HTTPAuth["auth = (username, password)"]
ResponseHandling["response.status_code == 200"]

CreateProject --> ShellScriptFormat
SonarScanExec --> WaitProcessing
ProjectExists --> SearchAPI
CreateProject --> CreateAPI

subgraph subGraph3 ["API Integration"]
    SearchAPI
    CreateAPI
    HTTPAuth
    ResponseHandling
    SearchAPI --> HTTPAuth
    CreateAPI --> HTTPAuth
    HTTPAuth --> ResponseHandling
end

subgraph subGraph2 ["Results Retrieval"]
    WaitProcessing
    QueryMeasures
    MeasuresAPI
    MetricKeys
    WaitProcessing --> QueryMeasures
    QueryMeasures --> MeasuresAPI
    MeasuresAPI --> MetricKeys
end

subgraph subGraph1 ["Scanning Process"]
    ShellScriptFormat
    SonarScanExec
    ScanParameters
    ShellScriptFormat --> ScanParameters
    ScanParameters --> SonarScanExec
end

subgraph subGraph0 ["SonarQube Project Management"]
    ProjectURL
    PlatformManager
    ProjectNaming
    ProjectExists
    CreateProject
    ProjectURL --> PlatformManager
    PlatformManager --> ProjectNaming
    ProjectNaming --> ProjectExists
    ProjectExists --> CreateProject
end
```

**Sources:** [openchecker/checkers/sonar_checker.py L14-L62](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py#L14-L62)

 [openchecker/checkers/sonar_checker.py L64-L103](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py#L64-L103)

 [openchecker/checkers/sonar_checker.py L105-L134](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py#L105-L134)

 [openchecker/checkers/sonar_checker.py L136-L173](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py#L136-L173)

## Document and License Compliance

The document compliance system validates project documentation and license information to ensure adherence to open source standards and best practices.

### Document Content Validation

The `document_checker` validates API documentation, build documentation, and license compliance using AI-powered content analysis.

```mermaid
flowchart TD

ProjectURL["project_url"]
GitClone["git clone project_url"]
DirectoryList["[project_name, project_name/doc, project_name/docs]"]
DocumentSearch["get_documents_in_directory()"]
MarkdownFiles["*.md, *.markdown files"]
DocTypes["doc_type: 'api-doc' or 'build-doc'"]
ContentTemplates["AI prompt templates"]
ChunkProcessing["chunk_size = 3000 characters"]
AIAnalysis["completion_with_backoff()"]
APITemplate["'assess whether the provided text offer a comprehensive<br>introduction to the use of software API'"]
APIResponse["'YES' or 'NO' response"]
APIChecker["api_doc_checker()"]
BuildTemplate["'assess whether the provided text offers a thorough<br>introduction to software compilation and packaging'"]
ExternalLink["'Unsupported markdown: link'"]
LinkCheck["do_link_include_check"]
BuildChecker["build_doc_checker()"]

MarkdownFiles --> DocTypes
DocTypes --> APITemplate
DocTypes --> BuildTemplate

subgraph subGraph3 ["Build Documentation Analysis"]
    BuildTemplate
    ExternalLink
    LinkCheck
    BuildChecker
    BuildTemplate --> ExternalLink
    ExternalLink --> LinkCheck
    LinkCheck --> BuildChecker
end

subgraph subGraph2 ["API Documentation Analysis"]
    APITemplate
    APIResponse
    APIChecker
    APITemplate --> APIResponse
    APIResponse --> APIChecker
end

subgraph subGraph1 ["Content Analysis Framework"]
    DocTypes
    ContentTemplates
    ChunkProcessing
    AIAnalysis
    DocTypes --> ContentTemplates
    ContentTemplates --> ChunkProcessing
    ChunkProcessing --> AIAnalysis
end

subgraph subGraph0 ["Document Discovery"]
    ProjectURL
    GitClone
    DirectoryList
    DocumentSearch
    MarkdownFiles
    ProjectURL --> GitClone
    GitClone --> DirectoryList
    DirectoryList --> DocumentSearch
    DocumentSearch --> MarkdownFiles
end
```

**Sources:** [openchecker/checkers/document_checker.py L11-L95](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py#L11-L95)

 [openchecker/checkers/document_checker.py L140-L159](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py#L140-L159)

 [openchecker/checkers/document_checker.py L161-L180](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py#L161-L180)

### README.OpenSource Compliance

The system validates `README.OpenSource` files for proper JSON structure and required compliance fields.

```mermaid
flowchart TD

ProjectClone["git clone if needed"]
ReadmeFile["README.OpenSource file"]
JSONParsing["json.load(file)"]
StructureValidation["isinstance(content, list)"]
RequiredKeys["['Name', 'License', 'License File',<br>'Version Number', 'Owner',<br>'Upstream URL', 'Description']"]
EntryValidation["all(key in entry for key in required_keys)"]
AllEntriesValid["Check all entries in list"]
ValidFormat["True, None"]
InvalidFormat["False, 'not properly formatted'"]
FileNotExists["False, 'does not exist'"]
CheckerResult["readme_opensource_checker()"]

StructureValidation --> RequiredKeys
AllEntriesValid --> ValidFormat
AllEntriesValid --> InvalidFormat
ReadmeFile --> FileNotExists

subgraph subGraph2 ["Compliance Results"]
    ValidFormat
    InvalidFormat
    FileNotExists
    CheckerResult
    ValidFormat --> CheckerResult
    InvalidFormat --> CheckerResult
    FileNotExists --> CheckerResult
end

subgraph subGraph1 ["Required Fields Validation"]
    RequiredKeys
    EntryValidation
    AllEntriesValid
    RequiredKeys --> EntryValidation
    EntryValidation --> AllEntriesValid
end

subgraph subGraph0 ["README.OpenSource Validation"]
    ProjectClone
    ReadmeFile
    JSONParsing
    StructureValidation
    ProjectClone --> ReadmeFile
    ReadmeFile --> JSONParsing
    JSONParsing --> StructureValidation
end
```

**Sources:** [openchecker/checkers/document_checker.py L97-L138](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py#L97-L138)

 [openchecker/checkers/document_checker.py L182-L200](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py#L182-L200)

 [openchecker/checkers/document_checker.py L118-L132](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py#L118-L132)

## Integration with Analysis Framework

All security checkers integrate with the broader OpenChecker analysis framework through standardized interfaces and shared utilities.

### Common Integration Patterns

| Component | Purpose | Usage |
| --- | --- | --- |
| `COMMAND` constant | Unique identifier for each checker | Used as key in `scan_results` |
| `project_url` parameter | Repository URL to analyze | Parsed by `platform_manager` |
| `res_payload` parameter | Shared results container | Updated with `scan_results[COMMAND]` |
| `access_token` parameter | Optional authentication | Required for webhook analysis |

The security checkers leverage shared utilities from the platform adapter system:

```mermaid
flowchart TD

GetPlatformType["get_platform_type()<br>Detect github/gitee/gitcode"]
ListWorkflowFiles["list_workflow_files()<br>Find .github/workflows/*.yml"]
PlatformManager["platform_manager.parse_project_url()<br>Extract owner_name, repo_path"]
SecurityPolicy["security_policy_checker<br>Uses: get_platform_type, platform_manager"]
TokenPerms["token_permissions_checker<br>Uses: get_platform_type, list_workflow_files"]
DangerousWorkflow["dangerous_workflow_checker<br>Uses: get_platform_type, list_workflow_files"]
Webhooks["webhooks_checker<br>Uses: URL parsing patterns"]

GetPlatformType --> SecurityPolicy
GetPlatformType --> TokenPerms
GetPlatformType --> DangerousWorkflow
ListWorkflowFiles --> TokenPerms
ListWorkflowFiles --> DangerousWorkflow
PlatformManager --> SecurityPolicy
PlatformManager --> TokenPerms
PlatformManager --> DangerousWorkflow

subgraph subGraph1 ["Security Checkers Usage"]
    SecurityPolicy
    TokenPerms
    DangerousWorkflow
    Webhooks
end

subgraph subGraph0 ["Shared Utilities"]
    GetPlatformType
    ListWorkflowFiles
    PlatformManager
end
```

**Sources:** [openchecker/checkers/security_policy_checker.py L5-L6](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/security_policy_checker.py#L5-L6)

 [openchecker/checkers/token_permissions_checker.py L8-L9](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/token_permissions_checker.py#L8-L9)

 [openchecker/checkers/dangerous_workflow_checker.py L5-L6](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/dangerous_workflow_checker.py#L5-L6)

 [openchecker/checkers/webhooks_checker.py L15-L16](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/webhooks_checker.py#L15-L16)