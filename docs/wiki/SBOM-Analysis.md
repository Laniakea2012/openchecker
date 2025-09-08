# SBOM Analysis

> **Relevant source files**
> * [openchecker/sbom/__init__.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/__init__.py)
> * [openchecker/sbom/sbom_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/sbom_checker.py)
> * [openchecker/sbom/test_sbom_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/test_sbom_checker.py)

## Purpose and Scope

The SBOM Analysis module provides Software Bill of Materials (SBOM) detection and compliance checking capabilities within OpenChecker's analysis framework. This system identifies SBOM files in both project source code and release artifacts, evaluating projects based on their SBOM availability and distribution practices according to OpenSSF Scorecard criteria.

For broader analysis tool integration, see [Checker Framework and Execution](/Laniakea2012/openchecker/4.2-checker-framework-and-execution). For supply chain security analysis, see [Supply Chain and Quality Analysis](/Laniakea2012/openchecker/4.4-supply-chain-and-quality-analysis).

## SBOM Detection Framework

The SBOM analysis system is built around a structured data model that represents SBOM files, their locations, and analysis results. The core framework defines several key data classes that work together to provide comprehensive SBOM detection and evaluation.

```mermaid
classDiagram
    class SBOMChecker {
        +sbom_file_pattern: re.Pattern
        +root_file_pattern: re.Pattern
        +release_look_back: int
        +check_sbom(request: CheckRequest) : CheckResult
        -_get_sbom_raw_data(request: CheckRequest) : SBOMData
        -_is_sbom_file(file_path: str) : bool
        -_check_sbom_releases(releases: List[Release]) : List[SBOM]
        -_check_sbom_source(file_list: List[str]) : List[SBOM]
        -_run_probes(raw_data: SBOMData) : List[Finding]
        -_evaluate_sbom(name: str, findings: List[Finding], logger) : CheckResult
    }
    class SBOMData {
        +sbom_files: List[SBOM]
    }
    class SBOM {
        +name: str
        +file: File
    }
    class File {
        +path: str
        +type: FileType
        +offset: int
        +end_offset: int
        +snippet: str
        +file_size: int
        +location() : Location
    }
    class Finding {
        +probe: str
        +outcome: Outcome
        +message: str
        +location: Optional[Location]
        +values: Dict[str, str]
    }
    class CheckResult {
        +name: str
        +score: int
        +reason: str
        +findings: List[Finding]
        +error: Optional[str]
    }
    class FileType {
        «enumeration»
        NONE
        SOURCE
        BINARY
        TEXT
        URL
        BINARY_VERIFIED
    }
    class Outcome {
        «enumeration»
        TRUE
        FALSE
        ERROR
    }
    SBOMChecker --> SBOMData
    SBOMData --> SBOM
    SBOM --> File
    File --> FileType
    SBOMChecker --> Finding
    Finding --> Outcome
    SBOMChecker --> CheckResult
    CheckResult --> Finding
```

Sources: [openchecker/sbom/sbom_checker.py L17-L110](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/sbom_checker.py#L17-L110)

The `SBOMChecker` class serves as the main entry point, coordinating the detection process through its `check_sbom` method. The system uses `FileType` enumeration to distinguish between source files, release artifacts (URLs), and other file types, enabling different handling strategies for each category.

## File Pattern Recognition

SBOM file detection relies on regular expression patterns that identify standard SBOM file formats and naming conventions. The system recognizes multiple SBOM standards including CycloneDX and SPDX formats.

```

```

Sources: [openchecker/sbom/sbom_checker.py L115-L122](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/sbom_checker.py#L115-L122)

 [openchecker/sbom/sbom_checker.py L179-L182](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/sbom_checker.py#L179-L182)

The `_is_sbom_file` method combines both pattern checks to ensure files meet SBOM naming conventions and are located appropriately within the project structure. The case-insensitive matching supports various capitalization patterns commonly found in real projects.

## Analysis Probes

The SBOM analysis employs two primary probes that evaluate different aspects of SBOM availability and distribution. These probes follow the OpenSSF Scorecard methodology for systematic evaluation.

```mermaid
sequenceDiagram
  participant SBOMChecker
  participant SBOMData
  participant hasSBOM Probe
  participant hasReleaseSBOM Probe
  participant Finding Results

  SBOMChecker->>SBOMData: "_get_sbom_raw_data()"
  SBOMData-->>SBOMChecker: "SBOMData with sbom_files"
  SBOMChecker->>hasSBOM Probe: "_run_has_sbom_probe(raw_data)"
  loop [SBOM files found]
    hasSBOM Probe->>Finding Results: "Finding(outcome=TRUE, message='Project has a SBOM file')"
    hasSBOM Probe->>Finding Results: "Finding(outcome=FALSE, message='Project does not have a SBOM file')"
    SBOMChecker->>hasReleaseSBOM Probe: "_run_has_release_sbom_probe(raw_data)"
    hasReleaseSBOM Probe->>Finding Results: "Finding(outcome=TRUE, message='Project publishes an SBOM file as part of a release or CICD')"
    hasReleaseSBOM Probe->>Finding Results: "Finding(outcome=FALSE, message='Project is not publishing an SBOM file as part of a release or CICD')"
  end
  Finding Results-->>SBOMChecker: "List[Finding]"
```

Sources: [openchecker/sbom/sbom_checker.py L224-L283](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/sbom_checker.py#L224-L283)

The `hasSBOM` probe evaluates whether any SBOM files exist in the project, while `hasReleaseSBOM` specifically checks for SBOM files distributed through release mechanisms. Each probe generates `Finding` objects with specific outcomes and descriptive messages.

## Scoring and Evaluation

The scoring system assigns points based on SBOM availability and distribution quality, with higher scores for projects that provide SBOM files in release artifacts compared to source-only distribution.

```mermaid
flowchart TD

Findings["List[Finding] from Probes"]
Validate["Validate Expected Probes:<br>hasSBOM, hasReleaseSBOM"]
ValidationError["Missing Probes"]
Error["CheckResult(score=0, error='Scorecard internal error')"]
Process["Process Findings"]
HasSBOM["hasSBOM = TRUE?"]
NoSBOM["CheckResult(score=0, reason='SBOM file not detected')"]
AddPoints1["Add 5 points"]
HasRelease["hasReleaseSBOM = TRUE?"]
AddPoints2["Add 5 more points<br>(Total: 10)"]
MaxScore["CheckResult(score=10, reason='SBOM file found in release artifacts')"]
SourceOnly["CheckResult(score=5, reason='SBOM file found in project')"]

Findings --> Validate
Validate --> ValidationError
ValidationError --> Error
Validate --> Process
Process --> HasSBOM
HasSBOM --> NoSBOM
HasSBOM --> AddPoints1
AddPoints1 --> HasRelease
HasRelease --> AddPoints2
AddPoints2 --> MaxScore
HasRelease --> SourceOnly
```

Sources: [openchecker/sbom/sbom_checker.py L285-L338](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/sbom_checker.py#L285-L338)

The `_evaluate_sbom` method implements a tiered scoring system where projects receive 5 points for having any SBOM file and an additional 5 points for distributing SBOM files through releases, achieving a maximum score of 10 points.

## Integration with Main System

The SBOM checker integrates with OpenChecker's broader analysis framework through the `check_sbom_for_project` function, which provides a simplified interface for project-level SBOM analysis.

```mermaid
flowchart TD

ProjectURL["Project URL"]
Setup["Environment Setup<br>SCORECARD_EXPERIMENTAL=true"]
Extract["Extract project_name<br>from URL"]
Walk["os.walk(project_name)<br>Directory Traversal"]
ScanFiles["Scan for SBOM files<br>using regex patterns"]
SourceSBOM["Collect Source SBOM files<br>type: 'source'"]
ReleaseSBOM["Check Release SBOM files<br>(simplified in current impl)"]
ReleaseData["Collect Release SBOM files<br>type: 'release'"]
Calculate["Calculate Score:<br>+5 for has_sbom<br>+5 for has_release_sbom"]
Result["Return Dict:<br>- sbom_files<br>- score<br>- has_sbom<br>- has_release_sbom<br>- status"]

ProjectURL --> Setup
Setup --> Extract
Extract --> Walk
Walk --> ScanFiles
ScanFiles --> SourceSBOM
ScanFiles --> ReleaseSBOM
ReleaseSBOM --> ReleaseData
SourceSBOM --> Calculate
ReleaseData --> Calculate
Calculate --> Result
```

Sources: [openchecker/sbom/sbom_checker.py L356-L426](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/sbom_checker.py#L356-L426)

The standalone function performs filesystem-based SBOM detection and returns a dictionary result format suitable for integration with OpenChecker's message-driven architecture. The system requires the `SCORECARD_EXPERIMENTAL` environment variable to enable SBOM checking functionality.

## Testing Infrastructure

The SBOM checker includes a comprehensive testing framework that validates detection capabilities across different file types and project structures.

```mermaid
flowchart TD

TempDir["Create Temporary Directory"]
ProjectDir["Create test-project directory"]
TestFiles["Create Test Files:<br>• README.md<br>• package.json<br>• test-sbom.spdx.json<br>• another-sbom.cdx.json<br>• not-sbom.txt"]
ChangeDir["Change to temp directory"]
RunTest["call check_sbom_for_project()"]
ValidateResults["Validate Results:<br>• status<br>• score<br>• has_sbom<br>• has_release_sbom<br>• sbom_files list"]
Cleanup["Restore original directory"]

TempDir --> ProjectDir
ProjectDir --> TestFiles
TestFiles --> ChangeDir
ChangeDir --> RunTest
RunTest --> ValidateResults
ValidateResults --> Cleanup
```

Sources: [openchecker/sbom/test_sbom_checker.py L13-L59](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/sbom/test_sbom_checker.py#L13-L59)

The test infrastructure creates realistic project structures with both valid SBOM files and non-SBOM files to verify proper pattern matching and scoring behavior. The `MockRepoClient` class enables testing without requiring actual repository connections.