# --------------------------------------------------------------------- project initialization
function dush_init_project() {
    param (
        [string] $project_name
    )


    $calling_script = Get-PSCallStack | Select-Object -Skip 1 -First 1 -ExpandProperty ScriptName
    $project_path = (Get-Item $calling_script ).Directory.FullName
    $main_func = $project_name

    # All metadata for the project will be stored in the dush_projects hashtable. Keys are project names and value are
    # project-specific hashtables containing properties. Some fields will be manually assigned in this function and
    # some will be read from an .ini file. This allows for the metadata to be shared between bash/powershell frontend
    # and python backend.
    if ($null -eq $dush_projects) {
        $global:dush_projects = @{}
    }
    $dush_projects[$project_name] = @{}
    $config = $dush_projects[$project_name]

    # Initialize some frontend-specific variables that will be used by Dush framework.
    $config["path"] = $project_path
    $config["is_loaded"] = $false
	$config["main_func"] = $main_func

    # Define known keys. All project's config.ini should define those keys and only those keys.
    $known_keys = ("name", "name_friendly", "dir_inside_root", "has_repository", "has_main_command", "has_bash_scripts",`
                   "has_python_scripts", "upstream_url", "upstream_main_branch", "upstream_dev_branch")

	# Read config from .ini file, that is shared with Python.
    foreach($line in Get-Content "$project_path/config.ini") {
        $key_value = $line -split '\s*=\s*'
        $key = $key_value[0].Trim()
        $value = $key_value[1].Trim()

        if ($known_keys -contains $key) {
            $config[$key] = $value
        } else {
            Write-Output "WARNING: Dush project $project_name defines unexpected setting `"$key`" in its config.ini."
        }
    }

    # Call reload on init if requested.
	if ($env:DUSH_ENABLE_AUTOLOAD) {
        _dush_project_reload $config 1 # TODO
    }

    # Validate all required keys are present
    $success = $true
    foreach($key in $known_keys) {
        if (-not $config.ContainsKey($key)) {
            Write-Output "ERROR: Dush project $project_name does not define config key `"$key`"."
            $success = $false
        }
    }
    if (-not $success) {
        return 1
    }

	# Generate project main, which will serve as a frontend for all interactions with this project.
    $project_main_definition = "function global:$main_func() { _dush_project_main $project_name `@args }"
    Invoke-Expression($project_main_definition)
}



# --------------------------------------------------------------------- project main
function _dush_project_main() {
    param (
        [string] $project_name
    )
    $config = $dush_projects[$project_name]
    $arg = $args[0]

	# The _dush_project_main function serves as a frontend for all operations doable on the project, so it has multiple
	# possible use cases. Some of these cases could be disabled, e.g. if has_repository=0, it means the project isn't
	# associated with a code repository. That means listing code repositories doesn't make any sense, so we don't even
	# try doing it and we can fallback to something else for convenience.
	#
	# Stage 1: try to dispatch based on first argument and project config.
	$has_main_command = $config["has_main_command"] -eq "1"
	$has_repository = $config["has_repository"] -eq "1"
	$dispatched = $false
    if ([string]::IsNullOrEmpty($arg)) {
        if ($has_repository) {
            _dush_project_dir_list $config
            $dispatched = $true
        }
    } elseif ($arg -eq "reload") {
        _dush_project_reload $config
        $dispatched = $true
        break
    } elseif ($arg -match '^[0-9]+$') {
        if ($has_repository) {
            _dush_project_dir_cd $config $arg
            $dispatched = $true
        }
    }

	# Stage 2: if we haven't dispatched in stage 1, try to call main command or reload command.
	if (-not $dispatched) {
		if ($has_main_command) {
			_dush_project_python_script $config @args
        } else {
			_dush_project_reload $config
        }
    }

    # Stage 3: Ensure reload has been done at least once.
    $is_loaded = $config["is_loaded"]
	if (-not $is_loaded) {
        _dush_project_reload $config
    }
}

# --------------------------------------------------------------------- Calling Python scripts
function _dush_call_python_script() {
    param(
        [string] $script_name
    )

    $env:PYTHONPATH = $env:DUSH_PATH # TODO restore this env
    python "$script_name" @args
}

function _dush_project_python_script() {
    param($config)

	$project_path = $config["path"]
	$project_name = $config["name"]

	$script_name="$project_path/$project_name.py"
	_dush_call_python_script "$script_name" @args
}



# --------------------------------------------------------------------- Managing project's code repositories
function _dush_project_dir_list() {
    param($config)

	$project_name = $config["name"]
	$project_name_friendly = $config["name_friendly"]
	$project_dir_inside_root = $config["dir_inside_root"]

	function get_branchname() {
        param($workspace)
        Push-Location $workspace

        if ($?) {
            $branch = & "git" branch --show-current
            if ([string]::IsNullOrEmpty($branch)) {
                $last_commit_date = & "git" log --format=%cr -1
                $result = "(FREE from $last_commit_date)"
            } else {
                $result = $branch
            }
        } else {
            $result = "(<ERROR>)"
        }

        Pop-Location
        return $result
	}

	Write-Output "$project_name_friendly workspaces:"
    $workspaces = Get-ChildItem $env:DUSH_WORKSPACE | Where-Object { $_.PSIsContainer -eq $true -and $_.Name -match "^$project_name[0-9]*$" }
	foreach ($workspace in $workspaces) {
        $workspace_path = $workspace.FullName
        $branch = get_branchname $workspace_path/$project_dir_inside_root
        Write-Output "    $workspace_path     $branch"
    }
}

function _dush_project_dir_cd() {
    param (
        $config,
        [int] $index
    )

	$project_name = $config["name"]
	$project_dir_inside_root = $config["dir_inside_root"]

	Set-Location "$env:DUSH_WORKSPACE/$project_name$index/$project_dir_inside_root"
    if ($?) {
        return
    }

    if ($index -eq "1") {
        Set-Location "$env:DUSH_WORKSPACE/$project_name/$project_dir_inside_root"
        if ($?) {
            return
        }
    }

	Write-Output "Could not cd"
	return 1
}



# --------------------------------------------------------------------- Reloading
function _dush_project_reload() {
	param($config, $silent)

	if ( $silent -ne "1" ) {
        $project_name = $config["name"]
        Write-Output "Reloading project $project_name"
    }

	$config["is_loaded"] = $true

	$has_main_command = $config["has_main_command"] -eq "1"
	$has_python_scripts = $config["has_python_scripts"] -eq "1"
	$has_bash_scripts = $config["has_bash_scripts"] -eq "1"

	if ($has_main_command) {
		_dush_generate_main_function_completion $config
    }

	if ($has_python_scripts) {
		_dush_load_python_scripts_as_powershell_functions $config
    }

    # TODO add has_powershell_scripts and update all projects
	if ($has_bash_scripts) {
		_dush_load_powershell_scripts_as_powershell_functions $config
    }
}

function _dush_generate_main_function_completion() {
    param($config)

    # TODO
    # I tried with Register-ArgumentCompleter for a bit, but it didn't work.
    # https://stackoverflow.com/questions/33497205/custom-powershell-tab-completion-for-a-specific-command
}

function _dush_load_python_scripts_as_powershell_functions() {
    param($config)

	$project_path = $config["path"]
	$main_func = $config["main_func"]

    $scripts = Get-ChildItem $project_path | Where-Object { $_.Extension -eq ".py" }
    foreach ($script_file in $scripts) {
        $script_name = $script_file.Basename
        $script_path = $script_file.FullName
        if ($script_name -eq $main_func) {
            continue
        }

        $function_definition = "function global:$script_name() { _dush_call_python_script $script_path `$args }"
        Invoke-Expression $function_definition
    }
}

function _dush_load_powershell_scripts_as_powershell_functions() {
    param($config)

	$project_path = $config["path"]
	$main_func = $config["main_func"]

    $scripts = Get-ChildItem -path $project_path -recurse | Where-Object { $_.Extension -eq ".ps1" }
    foreach ($script_file in $scripts) {
        $script_name = $script_file.Basename
        $script_path = $script_file.FullName
        if ($script_name -eq $main_func -or $script_name -eq "main") {
            continue
        }

        $function_definition = "function global:$script_name() { $script_path `$args }"
        Invoke-Expression $function_definition
    }
}



# --------------------------------------------------------------------- Other utilities
function dush_clear_caches() {
    Get-ChildItem $env:DUSH_PATH -Recurse |
        Where-Object { $_.Name -eq "commands.cache"} |
        ForEach-Object { Remove-Item $_.FullName }
}
