#!/bin/bash

# Initialize Dush framework.
if [ "$DUSH_INITIALIZED" != "1" ]; then
	DUSH_INITIALIZED=1

	# Check OS
	export DUSH_IS_WINDOWS=0
	export DUSH_IS_LINUX=0
	if uname -a | grep -q MINGW; then
		export DUSH_IS_WINDOWS=1
	elif uname -a | grep -q Linux; then
		export DUSH_IS_LINUX=1
	else
		echo "WARNING: Dush framework could not detect OS."
	fi

	# Prepare Python command. Gitbash on Windows inside mintty requires a special invocation.
	if [ -z "$DUSH_PYTHON_COMMAND" ]; then
		DUSH_PYTHON_COMMAND="python"
	fi
	if [ $DUSH_IS_WINDOWS = 1 ]; then
		# Detect whether we are running inside mintty, that does not connect to a TTY, so we
		# need to use winpty to run Python. The command ps -f returns a list of processes
		# with following columns: UID, PID, PPID, TTY, STIME, COMMAND. We use awk to check
		# column 2 (PID) matches parent PID of this process (bash) and then print column 6 (TTY).
		# In mintty, this column will be "mintty". In Windows Terminal it will be empty, because
		# parent PID is always 1 for some reason. But this is good enough to detect mintty.
		terminal="$(ps -f | awk -v pid=$PPID '$2 == pid { print $6 }')"
		if [[ "$terminal" =~ "/mintty" ]]; then
			DUSH_PYTHON_COMMAND="winpty -Xallow-non-tty -Xplain $DUSH_PYTHON_COMMAND"
		fi
	fi

	# Validate workspace path
	if [ -z "$DUSH_WORKSPACE" ]; then
		echo "ERROR: \$DUSH_WORKSPACE is not set"
	fi
	if ! [ -d "$DUSH_WORKSPACE" ]; then
		echo "ERROR: \$DUSH_WORKSPACE points to invalid directory - $DUSH_WORKSPACE"
	fi
	export DUSH_WORKSPACE="$DUSH_WORKSPACE"

	# Validate Dush path
	if [ -z "$DUSH_PATH" ]; then
		echo "ERROR: \$DUSH_PATH is not set"
	fi
	export DUSH_PATH="$DUSH_PATH"
fi



# Validate autoload
if [ -z "$DUSH_ENABLE_AUTOLOAD" ]; then
	DUSH_ENABLE_AUTOLOAD=0
fi
if [ "$DUSH_ENABLE_AUTOLOAD" != 0 ] && [ "$DUSH_ENABLE_AUTOLOAD" != 1 ]; then
	echo "ERROR: \$DUSH_ENABLE_AUTOLOAD is set to invalid value - $DUSH_ENABLE_AUTOLOAD. Setting to 0"
	DUSH_ENABLE_AUTOLOAD=0
fi



# --------------------------------------------------------------------- project initialization
dush_init_project() {
	local project_name="$1"
	local main_func="$project_name"

	# Get project path from calling script path. This is a bit sketchy, because it assumes the
	# calling script will always be a main.sh script located in root of project path directory.
	# But it simplifies the code and works as long as this design is followed.
	local project_path="${BASH_SOURCE[1]%/*}"

	# All metadata for the project will be stored in a global associative array. Some fields
	# will be manually assigned in this function and some will be read from an .ini file. This
	# allows for the metadata to be shared between bash frontend and python backend. In bash
	# we cannot directly access an array whose name contains variable and we have to use a
	# "name reference" (here called config).
	declare -Ag "dush_project_$project_name"
	declare -n config="dush_project_$project_name"

	# Initialize some Bash-specific variables that will be used by Dush framework.
	config["path"]="$project_path"
	config["is_loaded"]="0"
	config["main_func"]="$main_func"

	# Define known keys. All project's config.ini should define those keys and only those keys.
	local known_keys=(name name_friendly name_directory dir_inside_root has_repository has_main_command has_bash_scripts has_python_scripts
	                  has_git_submodules upstream_url upstream_main_branch upstream_dev_branch)

	# Read config from .ini file, that is shared with Python.
	while read -r line; do
		# Extract key/value pair. This method is not very robust, because it hardcodes the line format and requires
		# exactly one space before and after equals sign. It also gives weird results for empty values. Although,
		# it's quick and concise and I don't really care about robustness here.
		local key="${line%% =*}"
		local value="${line##*= }"
		value="${value%"${value##*[![:space:]]}"}" # Remove trailing whitespace

		# Check if the key is known
		local is_known=0
		for known_key in "${known_keys[@]}"; do
			if [ "$key" = "$known_key" ]; then
				is_known=1
				break
			fi
		done

		# Save the value to project config.
		if [ "$is_known" = "1" ]; then
			config["$key"]="$value"
		else
			echo "WARNING: Dush project $project_name defines unexpected setting \"$key\" in its config.ini"
		fi
	done < "$project_path/config.ini"

	# Call reload on init if requested.
	if [ "$DUSH_ENABLE_AUTOLOAD" = "1" ]; then
		_dush_project_reload 1
	fi

	# Validate all required keys are present
	local success=1
	for key in "${known_keys[@]}"; do
		if ! [ "${config[$key]+abc}" ]; then
			echo "ERROR: Dush project $project_name does not define config key $key"
			success=0
		fi
	done
	if [ "$success" = 0 ]; then
		return 1
	fi

	# Generate project main, which will serve as a frontend for all interactions with this project.
	local project_main_definition="$main_func() { _dush_project_main $1 \"\$@\" ; return \$? ; }"
	eval "$project_main_definition"
}



# --------------------------------------------------------------------- project main
_dush_project_main() {
	# Parse arguments. Project name will be passed automatically by code generated in dush_init_project(). The
	# rest of the arguments will come from the user. We'll shift args by one to omit the project name, so that
	# the "$@" expression doesn't contain it.
	local project_name="$1"
	local arg="$2"
	shift

	# Declare a name reference named "config" for associative array with a variable name. This definition will be
	# visible by all subroutines called by the project main, so they will be access all project metadata.
	declare -n config="dush_project_$project_name"

	# The _dush_project_main function serves as a frontend for all operations doable on the project, so it has multiple
	# possible use cases. Some of these cases could be disabled, e.g. if has_repository=0, it means the project isn't
	# associated with a code repository. That means listing code repositories doesn't make any sense, so we don't even
	# try doing it and we can fallback to something else for convenience.
	#
	# Stage 1: try to dispatch based on first argument and project config. The cryptic glob *[!0-9]*) matches nearly
	# everything, except for only-digits strings. So the last *) glob will match only numbers.
	local has_main_command=${config["has_main_command"]}
	local has_repository=${config["has_repository"]}
	local dispatched=0
	case "$arg" in
		'')
			if [ "$has_repository" = "1" ]; then
				_dush_project_dir_list
				dispatched=1
			fi
			;;
		"reload")
			_dush_project_reload
			dispatched=1
			;;
		*[!0-9]*)
			dispatched=0 # fallback
			;;
		*)
			if [ "$has_repository" = "1" ]; then
				_dush_project_dir_cd "$arg"
				dispatched=1
			fi
			;;
	esac

	# Stage 2: if we haven't dispatched in stage 1, try to call main command or reload command.
	exit_value=0
	if [ "$dispatched" = "0" ]; then
		if [ "$has_main_command" = "1" ]; then
			_dush_project_python_script "$@"
			exit_value=$?
		else
			_dush_project_reload
		fi
	fi

	# Stage 3: Ensure reload has been done at least once.
	if [ "${config["is_loaded"]}" = 0 ]; then
		_dush_project_reload
	fi

	return $exit_value
}



# --------------------------------------------------------------------- Calling Python scripts
_dush_call_python_script() {
	local script_name="$1"
	shift
	PYTHONPATH=$DUSH_PATH $DUSH_PYTHON_COMMAND "$script_name" "$@"
	return $?
}

_dush_project_python_script() {
	local project_path=${config["path"]}
	local project_name=${config["name"]}

	local script_name="$project_path/$project_name.py"
	_dush_call_python_script "$script_name" "$@"
	return $?
}



# --------------------------------------------------------------------- Managing project's code repositories
_dush_project_dir_list() {
	local project_directory_name=${config["name_directory"]}
	local project_name_friendly=${config["name_friendly"]}
	local project_dir_inside_root=${config["dir_inside_root"]}

	get_branchname() {
        local workspace="$1"
        cd "$workspace" 2>/dev/null || {
			echo "(<ERROR>)"
			return
		}
		local branch="$(git branch --show-current)"
		if [ -n "$branch" ]; then
			echo "($branch)"
		else
			echo "(FREE from $(git log --format=%cr -1))"
		fi
	}

	echo "$project_name_friendly workspaces:"
	for workspace in $(find $DUSH_WORKSPACE/ -maxdepth 1 -regex ".*/$project_directory_name""[0-9]*$" | sort); do
		branch="$(get_branchname "$workspace/$project_dir_inside_root")"
		echo "    $workspace     $branch"
	done
}

_dush_project_dir_cd() {
	local index="$1"
	local project_directory_name=${config["name_directory"]}
	local project_dir_inside_root=${config["dir_inside_root"]}

	cd "$DUSH_WORKSPACE/$project_directory_name$index/$project_dir_inside_root" 2>/dev/null && return 0

	if [ "$index" = 1 ]; then
		cd "$DUSH_WORKSPACE/$project_directory_name/$project_dir_inside_root" 2>/dev/null && return 0
	fi

	echo "Could not cd to $project_directory_name directory."
	return 1
}



# --------------------------------------------------------------------- Reloading
_dush_project_reload() {
	local silent="$1"
	if [ "$silent" != "1" ]; then
		echo "Reloading project ${config[name]}"
	fi

	config["is_loaded"]="1"

	local has_main_command=${config["has_main_command"]}
	local has_python_scripts=${config["has_python_scripts"]}
	local has_bash_scripts=${config["has_bash_scripts"]}

	if [ "$has_main_command" = 1 ]; then
		_dush_generate_main_function_completion
	fi

	if [ "$has_python_scripts" = 1 ]; then
		_dush_load_python_scripts_as_bash_functions
	fi

	if [ "$has_bash_scripts" = 1 ]; then
		_dush_load_bash_scripts
	fi
}

_dush_generate_main_function_completion() {
	local project_path=${config["path"]}

	local cache_file="$project_path/commands.cache"
	local args=
	if [ -f "$cache_file" ]; then
		read -r args < "$cache_file"
	else
		args="$(_dush_project_python_script list -- -q | tr -d '\n' | tr -d '\r')"
		printf "$args\n" > "$cache_file"
	fi

	complete -W "$args reload" "$project_name"
}

_dush_load_python_scripts_as_bash_functions() {
	local project_path=${config["path"]}
	local main_func=${config["main_func"]}

	for script_file_raw in "$project_path"/*.py "$project_path"/**/*.py; do
		# Normalize path to forward slashes
		script_file="${script_file_raw//\\//}"

		# Skip if file does not exist, which may happen if glob does not match anything and it returns the pattern itself.
		if [ ! -e "$script_file" ]; then
			continue
		fi

		# Skip OS-specific dirs
		if  [[ "$script_file" == *"/$forbidden_dir/"* ]]; then
			continue
		fi

		local script_name="${script_file%.*}"      # Substring removal to remove the extension
		local script_name="${script_name##*/}"   # Substring removal to remove the directory path
		if [ "$script_name" != "$main_func" ]; then
			local function_definition="$script_name() { _dush_call_python_script \"$script_file\" \"\$@\" ; return \$? ; }"
			eval "$function_definition"
		fi
	done
}

_dush_load_bash_scripts() {
	local project_path=${config["path"]}

	if [ "$DUSH_IS_LINUX" == 1 ]; then
		local forbidden_dir="windows"
	else
		local forbidden_dir="linux"
	fi

	for script_file_raw in "$project_path"/*.sh "$project_path"/**/*.sh; do
		# Normalize path to forward slashes
		script_file="${script_file_raw//\\//}"

		# Skip if file does not exist, which may happen if glob does not match anything and it returns the pattern itself.
		if [ ! -e "$script_file" ]; then
			continue
		fi

		# Skip OS-specific dirs and main.sh
		if  [[ "$script_file" == *"/$forbidden_dir/"* ]] || \
			[[ "$script_file" == */main.sh ]]; then
			continue
		fi

		. "$script_file"
	done
}

# --------------------------------------------------------------------- Other utilities
dush_clear_caches() {
	local dush_path="$DUSH_PATH"
	if [ "$DUSH_IS_WINDOWS" = 1 ]; then
		dush_path="$(echo "$dush_path" | sed -E "s/\\\\/\//g" | sed -E "s/(C):\//\/\l\1\//g")"
	fi
	find "$dush_path" -name "commands.cache" | xargs rm
}
