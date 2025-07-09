def _get_project_name(project_url):
    return f"""project_name=$(basename {project_url} | sed 's/\.git$//') > /dev/null"""

def _clone_project(project_url, depth=False):
    depth_flag = "--depth=1" if depth else ""
    return f"""if [ ! -e "$project_name" ]; then
    GIT_ASKPASS=/bin/true git clone {depth_flag} {project_url} > /dev/null
fi"""

BASE_SCRIPT = _get_project_name("{project_url}") + "\n" + _clone_project("{project_url}")

download_checkout_shell_script = f"""
    {BASE_SCRIPT}
    cd "$project_name"

    if [ {{version_number}} != "None" ]; then
        if git tag | grep -q "^{{version_number}}$"; then
            git checkout "{{version_number}}" && \\
            echo "成功切换到标签 {{version_number}}" || \\
            echo "切换到标签 {{version_number}} 失败"
        fi
    fi
    """

generate_lock_files_shell_script = f"""
    {BASE_SCRIPT}
    if [ -e "$project_name/package.json" ] && [ ! -e "$project_name/package-lock.json" ]; then
        cd $project_name && npm install && rm -fr node_modules > /dev/null
        echo "Generate lock files for $project_name with command npm."
    fi
    if [ -e "$project_name/oh-package.json5" ] && [ ! -e "$project_name/oh-package-lock.json5" ]; then
        cd $project_name && ohpm install && rm -fr oh_modules > /dev/null
        echo "Generate lock files for $project_name with command ohpm."
    fi
    """

osv_scanner_shell_script = f"""
    {_get_project_name("{project_url}")}
    {_clone_project("{project_url}", depth=True)}

    if [ -f "$project_name/oh-package-lock.json5" ] && [ ! -f "$project_name/package-lock.json" ]; then
        mv $project_name/oh-package-lock.json5 $project_name/package-lock.json > /dev/null
        rename_flag=1
    fi

    osv-scanner --format json -r $project_name > $project_name/result.json
    cat $project_name/result.json

    if [ -v rename_flag ]; then
        mv $project_name/package-lock.json $project_name/oh-package-lock.json5 > /dev/null
    fi
    """

scancode_shell_script = f"""
    {_get_project_name("{project_url}")}
    {_clone_project("{project_url}", depth=True)}
    scancode -lc --json-pp scan_result.json $project_name --license-score 90 -n 4 > /dev/null
    cat scan_result.json
    rm -rf scan_result.json > /dev/null
    """

sonar_scanner_shell_script = f"""
    {_get_project_name("{project_url}")}
    {_clone_project("{project_url}", depth=True)}
    cp -r $project_name ~/ && cd ~
    sonar-scanner \\
        -Dsonar.projectKey={{sonar_project_name}} \\
        -Dsonar.sources=$project_name \\
        -Dsonar.host.url=http://{{sonar_config['host']}}:{{sonar_config['port']}} \\
        -Dsonar.token={{sonar_config['token']}} \\
        -Dsonar.exclusions=**/*.java
    rm -rf $project_name > /dev/null
    """

dependency_checker_shell_script = f"""
    {_get_project_name("{project_url}")}
    {_clone_project("{project_url}", depth=True)}
    ort -P ort.analyzer.allowDynamicVersions=true analyze -i $project_name -o $project_name -f JSON > /dev/null
    cat $project_name/analyzer-result.json
    """

readme_checker_shell_script = f"""
    {_get_project_name("{project_url}")}
    {_clone_project("{project_url}", depth=True)}
    find "$project_name" -type f \\( -name "README*" -o -name "docs/README*" \\) -print
    """

maintainers_checker_shell_script = f"""
    {_get_project_name("{project_url}")}
    {_clone_project("{project_url}", depth=True)}
    find "$project_name" -type f \\( -iname "MAINTAINERS*" -o -iname "COMMITTERS*" -o -iname "OWNERS*" -o -iname "CODEOWNERS*" \\) -print
    """

languages_detector_shell_script = f"""
    {_get_project_name("{project_url}")}
    {_clone_project("{project_url}", depth=True)}
    github-linguist $project_name --breakdown --json
    """

oat_scanner_shell_script = f"""
    {_get_project_name("{project_url}")}
    {_clone_project("{project_url}", depth=True)}                
    if [ ! -f "$project_name/OAT.xml" ]; then
        echo "OAT.xml not found in the project root directory."
        exit 1   
    fi
    java -jar ohos_ossaudittool-2.0.0.jar -mode s -s $project_name -r $project_name/oat_out -n $project_name > /dev/null            
    report_file="$project_name/oat_out/single/PlainReport_$project_name.txt"
    [ -f "$report_file" ] && cat "$report_file"                        
    """

remove_source_code_shell_script = f"""
    {_get_project_name("{project_url}")}
    if [ -e "$project_name" ]; then
        rm -rf $project_name > /dev/null
    fi
    """

license_detector_shell_script = f"""
    {_get_project_name("{project_url}")}
    {_clone_project("{project_url}", depth=True)}
    licensee detect "$project_name" --json
    rm -rf $project_name > /dev/null
    """

shell_script_handlers = {
    "download-checkout": download_checkout_shell_script,
    "generate-lock_files": generate_lock_files_shell_script,
    "osv-scanner": osv_scanner_shell_script,
    "scancode": scancode_shell_script,
    "sonar-scanner": sonar_scanner_shell_script,
    "dependency-checker": dependency_checker_shell_script,
    "readme-checker": readme_checker_shell_script,
    "maintainers-checker": maintainers_checker_shell_script,
    "languages-detector": languages_detector_shell_script,
    "oat-scanner": oat_scanner_shell_script,
    "remove-source-code": remove_source_code_shell_script,
    "license-detector": license_detector_shell_script,
}