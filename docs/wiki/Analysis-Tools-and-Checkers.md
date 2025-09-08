# Analysis Tools and Checkers

> **Relevant source files**
> * [Dockerfile](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/Dockerfile)
> * [config/ohpm_repo.json](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/config/ohpm_repo.json)
> * [openchecker/checkers/binary_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/binary_checker.py)
> * [openchecker/checkers/changed_files_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/changed_files_checker.py)
> * [openchecker/checkers/document_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py)
> * [openchecker/checkers/release_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/release_checker.py)
> * [openchecker/checkers/sonar_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py)
> * [openchecker/checkers/url_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/url_checker.py)
> * [openchecker/user_manager.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/user_manager.py)
> * [scripts/entrypoint.sh](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/entrypoint.sh)
> * [test/test_server.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/test/test_server.py)

This document covers the comprehensive analysis tools ecosystem and checker framework within OpenChecker. The system provides automated analysis capabilities for software projects including vulnerability scanning, license detection, code quality assessment, and compliance checking through a containerized environment with integrated external tools.

For information about the core agent system that executes these tools, see [Core Architecture](/Laniakea2012/openchecker/2-core-architecture). For details about external service integration and platform adapters, see [Platform Integration and External Services](/Laniakea2012/openchecker/5-platform-integration-and-external-services).

## Container Environment and Tool Installation

OpenChecker operates within a comprehensive Docker-based environment that includes numerous analysis tools and package managers. The container setup provides a unified runtime for all analysis operations.

### Multi-Stage Build Architecture

```mermaid
flowchart TD

OSVBuilder["osv-scanner-builder<br>alpine + osv-scanner"]
OATBuilder["oat_builder<br>maven + OpenHarmony OAT"]
MainStage["python:3.9-bullseye<br>Main Runtime Stage"]
ScanCode["scancode-toolkit<br>v32.1.0"]
SonarScanner["sonar-scanner-cli<br>v6.1.0.4477"]
ORT["oss-review-toolkit<br>v25.0.0"]
Scorecard["scorecard<br>v5.2.1"]
OSVTool["osv-scanner<br>from alpine"]
OATTool["ohos_ossaudittool<br>v2.0.0.jar"]
Ruby["Ruby 3.1.6<br>+ RVM"]
Java["OpenJDK 11"]
NodeJS["Node.js 18.x<br>+ npm/pnpm/yarn"]
Python["Python 3.9<br>+ pip packages"]
GemTools["github-linguist<br>cocoapods<br>ruby-licensee"]
NPMTools["pnpm<br>yarn<br>bower"]
OtherTools["ohpm<br>cloc<br>sbt"]

MainStage --> ScanCode
MainStage --> SonarScanner
MainStage --> ORT
MainStage --> Scorecard
MainStage --> OSVTool
MainStage --> OATTool
MainStage --> Ruby
MainStage --> Java
MainStage --> NodeJS
MainStage --> Python
Ruby --> GemTools
NodeJS --> NPMTools
MainStage --> OtherTools

subgraph subGraph3 ["Package Managers"]
    GemTools
    NPMTools
    OtherTools
end

subgraph subGraph2 ["Language Runtimes"]
    Ruby
    Java
    NodeJS
    Python
end

subgraph subGraph1 ["Installed Tools"]
    ScanCode
    SonarScanner
    ORT
    Scorecard
    OSVTool
    OATTool
end

subgraph subGraph0 ["Build Stages"]
    OSVBuilder
    OATBuilder
    MainStage
    OSVBuilder --> MainStage
    OATBuilder --> MainStage
end
```

The container environment includes specialized tools for different analysis domains:

* **Vulnerability Scanning**: `osv-scanner` for security vulnerability detection
* **License Analysis**: `scancode-toolkit` for comprehensive license scanning
* **Code Quality**: `sonar-scanner-cli` for static code analysis integration
* **Supply Chain**: `oss-review-toolkit` (ORT) for dependency analysis
* **Security Assessment**: `scorecard` for security posture evaluation
* **OpenHarmony Compliance**: `ohos_ossaudittool` for ecosystem-specific auditing

Sources: [Dockerfile L1-L91](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/Dockerfile#L1-L91)

### Language Runtime and Package Manager Support

The container provides comprehensive language support enabling analysis across diverse technology stacks:

| Language/Runtime | Tools Installed | Package Managers |
| --- | --- | --- |
| Ruby | RVM, Ruby 3.1.6, github-linguist, cocoapods, ruby-licensee | gem |
| Java | OpenJDK 11, sbt | maven, sbt |
| Node.js | Node.js 18.x | npm, pnpm, yarn, bower |
| Python | Python 3.9, criticality_score | pip |
| OpenHarmony | ohpm_cli_tool, pm-cli.js | ohpm |
| Generic | cloc (line counting) | - |

Sources: [Dockerfile L52-L87](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/Dockerfile#L52-L87)

## Checker Framework and Execution

The checker framework provides modular analysis capabilities through individual checker modules that can be invoked independently or as part of comprehensive project analysis workflows.

### Core Checker Architecture

```mermaid
flowchart TD

URLChecker["url_checker<br>URL Accessibility"]
BinaryChecker["binary_checker<br>Binary File Detection"]
DocumentChecker["document_checker<br>API/Build Documentation"]
ReleaseChecker["release_checker<br>Release Content Analysis"]
SonarChecker["sonar_checker<br>Code Quality Integration"]
ChangedFilesChecker["changed_files_checker<br>Git Diff Analysis"]
ShellExec["shell_exec()<br>common.py"]
ScriptHandlers["shell_script_handlers<br>constans.py"]
BinaryScript["binary_checker.sh<br>scripts/"]
SonarQube["SonarQube Server<br>API Integration"]
GitPlatforms["Platform Adapters<br>GitHub/Gitee/GitCode"]
LLMServices["LLM Services<br>Document Analysis"]

URLChecker --> ShellExec
BinaryChecker --> ScriptHandlers
BinaryChecker --> BinaryScript
DocumentChecker --> LLMServices
ReleaseChecker --> GitPlatforms
SonarChecker --> SonarQube
ChangedFilesChecker --> ShellExec

subgraph subGraph2 ["External Integrations"]
    SonarQube
    GitPlatforms
    LLMServices
end

subgraph subGraph1 ["Execution Framework"]
    ShellExec
    ScriptHandlers
    BinaryScript
end

subgraph subGraph0 ["Checker Modules"]
    URLChecker
    BinaryChecker
    DocumentChecker
    ReleaseChecker
    SonarChecker
    ChangedFilesChecker
end
```

### File Change Detection System

The `changed_files_detector` function provides Git-based analysis for tracking project modifications:

```mermaid
flowchart TD

ProjectURL["project_url"]
CommitHash["commit_hash"]
ResPayload["res_payload"]
GitDiff["git diff<br>--name-only<br>--diff-filter"]
DiffTypes["A: Added<br>C: Copied<br>D: Deleted<br>M: Modified<br>R: Renamed"]
ChangedFiles["changed_files<br>(ACDMRTUXB)"]
NewFiles["new_files<br>(A)"]
RenameFiles["rename_files<br>(R)"]
DeletedFiles["deleted_files<br>(D)"]
ModifiedFiles["modified_files<br>(M)"]

ProjectURL --> GitDiff
CommitHash --> GitDiff
DiffTypes --> ChangedFiles
DiffTypes --> NewFiles
DiffTypes --> RenameFiles
DiffTypes --> DeletedFiles
DiffTypes --> ModifiedFiles
ChangedFiles --> ResPayload
NewFiles --> ResPayload
RenameFiles --> ResPayload
DeletedFiles --> ResPayload
ModifiedFiles --> ResPayload

subgraph subGraph2 ["Output Categories"]
    ChangedFiles
    NewFiles
    RenameFiles
    DeletedFiles
    ModifiedFiles
end

subgraph subGraph1 ["Git Operations"]
    GitDiff
    DiffTypes
    GitDiff --> DiffTypes
end

subgraph subGraph0 ["Input Parameters"]
    ProjectURL
    CommitHash
    ResPayload
end
```

The system uses Git's `diff-filter` capabilities to categorize file changes, enabling targeted analysis of specific change types.

Sources: [openchecker/checkers/changed_files_checker.py L10-L77](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/changed_files_checker.py#L10-L77)

### URL Accessibility Validation

The `url_checker` module provides basic connectivity validation for project URLs:

* **Function**: `url_checker(project_url, res_payload)`
* **Method**: HTTP GET request with 10-second timeout
* **Output**: Status code and accessibility boolean
* **Error Handling**: Exception capture with error message logging

Sources: [openchecker/checkers/url_checker.py L8-L25](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/url_checker.py#L8-L25)

## Security and Compliance Analysis

The security analysis capabilities focus on vulnerability detection, binary file identification, and compliance verification through multiple specialized tools and custom implementations.

### Binary File Detection System

```mermaid
flowchart TD

BinaryChecker["binary_checker()<br>Python Function"]
BinaryScript["binary_checker.sh<br>Shell Script"]
ShellExec["shell_exec()<br>Execution Wrapper"]
BinaryFiles["binary_file_list<br>Executable Files"]
BinaryArchives["binary_archive_list<br>Archive Files"]
ResultParsing["String Parsing<br>'Binary file found:'<br>'Binary archive found:'"]
PayloadUpdate["res_payload<br>scan_results update"]

BinaryScript --> ResultParsing
ResultParsing --> BinaryFiles
ResultParsing --> BinaryArchives
BinaryFiles --> PayloadUpdate
BinaryArchives --> PayloadUpdate

subgraph subGraph2 ["Output Processing"]
    ResultParsing
    PayloadUpdate
end

subgraph subGraph1 ["Detection Categories"]
    BinaryFiles
    BinaryArchives
end

subgraph subGraph0 ["Binary Detection Process"]
    BinaryChecker
    BinaryScript
    ShellExec
    BinaryChecker --> ShellExec
    ShellExec --> BinaryScript
end
```

The binary checker identifies potentially problematic binary files within source repositories by delegating to a shell script and parsing structured output.

Sources: [openchecker/checkers/binary_checker.py L9-L42](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/binary_checker.py#L9-L42)

### Document Compliance Analysis

The document checker system provides AI-powered analysis of documentation completeness and README.OpenSource file validation:

#### API and Build Documentation Analysis

* **Function**: `check_doc_content(project_url, doc_type)`
* **Document Types**: `"api-doc"` and `"build-doc"`
* **Analysis Method**: LLM-based content evaluation with chunked processing
* **File Discovery**: Recursive search in `project/`, `project/doc/`, `project/docs/`
* **LLM Integration**: Uses `completion_with_backoff()` for reliable AI analysis

#### README.OpenSource Validation

* **Function**: `check_readme_opensource(project_url)`
* **Format**: JSON structure validation
* **Required Fields**: Name, License, License File, Version Number, Owner, Upstream URL, Description
* **Validation**: JSON parsing and required key verification

Sources: [openchecker/checkers/document_checker.py L11-L200](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py#L11-L200)

## Supply Chain and Quality Analysis

The supply chain analysis encompasses release content verification, signed release detection, and code quality integration through SonarQube.

### Release Content Analysis System

```mermaid
flowchart TD

GetReleases["get_all_releases_with_assets()<br>Platform Adapter Integration"]
CheckContents["check_release_contents()<br>Content Type Analysis"]
CheckSigned["check_signed_release()<br>Signature Verification"]
NotesAnalysis["Notes Analysis<br>changelog, releasenotes<br>release_notes, release"]
SBOMAnalysis["SBOM Analysis<br>.cdx.json, .spdx<br>.spdx.json, .spdx.xml"]
SigExtensions[".minisig, .asc, .sig<br>.sign, .sigstore<br>.intoto.jsonl"]
ZipballURL["zipball_url<br>Release Archive Download"]
AssetsParsing["assets<br>Release Assets Parsing"]

CheckContents --> NotesAnalysis
CheckContents --> SBOMAnalysis
CheckContents --> ZipballURL
CheckSigned --> SigExtensions
CheckSigned --> AssetsParsing

subgraph subGraph3 ["Platform Integration"]
    ZipballURL
    AssetsParsing
end

subgraph subGraph2 ["Signature Detection"]
    SigExtensions
end

subgraph subGraph1 ["Content Analysis Types"]
    NotesAnalysis
    SBOMAnalysis
end

subgraph subGraph0 ["Release Analysis Functions"]
    GetReleases
    CheckContents
    CheckSigned
    GetReleases --> CheckContents
    GetReleases --> CheckSigned
end
```

The release analysis system provides comprehensive validation of release artifacts including:

* **Release Notes**: Automated detection of changelog and release documentation
* **SBOM Files**: Software Bill of Materials validation in multiple formats
* **Digital Signatures**: Cryptographic signature verification across common formats
* **Platform Support**: GitHub, Gitee, and GitCode compatibility

Sources: [openchecker/checkers/release_checker.py L14-L282](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/release_checker.py#L14-L282)

### SonarQube Integration Framework

The SonarQube integration provides automated code quality analysis with project lifecycle management:

#### Project Management Workflow

```mermaid
sequenceDiagram
  participant sonar_checker()
  participant platform_manager
  participant SonarQube Server
  participant shell_exec()

  sonar_checker()->>platform_manager: "parse_project_url()"
  platform_manager-->>sonar_checker(): "owner_name, repo_name"
  sonar_checker()->>SonarQube Server: "_check_sonar_project_exists()"
  SonarQube Server-->>sonar_checker(): "project_exists: boolean"
  loop [Project Does Not Exist]
    sonar_checker()->>SonarQube Server: "_create_sonar_project()"
    SonarQube Server-->>sonar_checker(): "project_created"
  end
  sonar_checker()->>shell_exec(): "shell_script_handlers['sonar-scanner']"
  shell_exec()-->>sonar_checker(): "scan_complete"
  sonar_checker()->>SonarQube Server: "_query_sonar_measures()"
  SonarQube Server-->>sonar_checker(): "analysis_results"
```

#### Metrics Collection

The system queries specific SonarQube metrics after analysis completion:

* **Coverage**: Test coverage percentage
* **Complexity**: Cyclomatic complexity measurement
* **Duplicated Lines Density**: Code duplication percentage
* **Lines**: Total lines of code

Sources: [openchecker/checkers/sonar_checker.py L14-L173](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py#L14-L173)

## SBOM Analysis

Software Bill of Materials (SBOM) analysis is integrated into the release content analysis system, providing automated detection and validation of SBOM files within project releases.

### SBOM Format Support

The system supports multiple SBOM formats through pattern matching:

| Format | File Extensions | Pattern |
| --- | --- | --- |
| CycloneDX | `.cdx.json`, `.cdx.xml` | Case-insensitive regex |
| SPDX | `.spdx`, `.spdx.json`, `.spdx.xml` | Multiple format support |
| SPDX YAML | `.spdx.yml`, `.spdx.yaml` | YAML variants |
| SPDX RDF | `.spdx.rdf`, `.spdx.rdf.xml` | RDF serialization |

### SBOM Detection Workflow

```mermaid
flowchart TD

ReleaseArchive["Release Archive<br>zipball download"]
PatternMatching["Pattern Matching<br>_get_file_patterns('sbom')"]
FileValidation["File Validation<br>Format verification"]
CycloneDX["CycloneDX<br>.cdx.json/.cdx.xml"]
SPDX["SPDX<br>.spdx/.spdx.json"]
SPDY_YAML["SPDX YAML<br>.spdx.yml/.spdx.yaml"]
SPDX_RDF["SPDX RDF<br>.spdx.rdf/.spdx.rdf.xml"]

PatternMatching --> CycloneDX
PatternMatching --> SPDX
PatternMatching --> SPDY_YAML
PatternMatching --> SPDX_RDF
CycloneDX --> FileValidation
SPDX --> FileValidation
SPDY_YAML --> FileValidation
SPDX_RDF --> FileValidation

subgraph subGraph1 ["Supported Formats"]
    CycloneDX
    SPDX
    SPDY_YAML
    SPDX_RDF
end

subgraph subGraph0 ["SBOM Detection Process"]
    ReleaseArchive
    PatternMatching
    FileValidation
    ReleaseArchive --> PatternMatching
end
```

The SBOM analysis is performed as part of the comprehensive release checker workflow, providing automated compliance verification for software supply chain transparency requirements.

Sources: [openchecker/checkers/release_checker.py L153-L171](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/release_checker.py#L153-L171)