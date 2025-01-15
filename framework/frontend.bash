#!/bin/bash

# Prepare Python command. Gitbash on Windows requires a special invocation, otherwise it
# hangs for some reason.
if [ -z "$DUSH_PYTHON_COMMAND" ]; then
	DUSH_PYTHON_COMMAND="python"
fi
if uname | grep -q MINGW; then
	DUSH_PYTHON_COMMAND="winpty -Xallow-non-tty -Xplain $DUSH_PYTHON_COMMAND"
fi

# Validate workspace path
if [ -z "$DUSH_WORKSPACE" ]; then
	echo "ERROR: \$DUSH_WORKSPACE is not set"
fi
if ! [ -d "$DUSH_WORKSPACE" ]; then
	echo "ERROR: \$DUSH_WORKSPACE points to invalid directory - $DUSH_WORKSPACE"
fi
export DUSH_WORKSPACE="$DUSH_WORKSPACE"

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
	local main_function_name="$2"
	local reload_function_name="$3"
	local project_path="$(dirname "${BASH_SOURCE[1]}")" # this is a bit sketchy...

	# All metadata for the project will be stored in a global associative array. Some fields
	# will be manually assigned in this function and some will be read from an .ini file. This
	# allows for the metadata to be shared between bash frontend and python backend. In bash
	# we cannot directly access an array whose name contains variable and we have to use a
	# "name reference" (here called config).
	declare -Ag "dush_project_$project_name"
	declare -n config="dush_project_$project_name"

	# Main function is generated automatically. It is optional and can be skipped by specifying
	# an empty main function name. This would typically done for a project, that's just a set of
	# Bash/Python scripts with no single main file.
	if [ -n "$main_function_name" ]; then
		local function_definition="$main_function_name() { dush_project_main $1 \""\$@"\" ; }"
		eval "$function_definition"
	fi

	# Read config from .ini file, that is shared with Python.
	while read -r line; do
		key="${line%% =*}"
		value="${line##*= }"
		config["$key"]="$value"
	done < "$project_path/config.ini"

	# Initialize some Bash-specific variables that will be used by Dush framework.
	config["path"]="$project_path"
	config["is_loaded"]="0"
	config["main_func"]="$main_function_name"
	config["reload_func"]="$reload_function_name"

	# Call reload on init if requested.
	if [ "$DUSH_ENABLE_AUTOLOAD" = "1" ]; then
		_dush_call_lazy_reload
	fi
}


# --------------------------------------------------------------------- project main and its subroutines
dush_project_main() {
	declare -n config="dush_project_$1"
	local arg="$2"
	shift # Shift args, so that "$@" contains only user specified arguments

	# Ensure reload is done
	_dush_call_lazy_reload

	# If project_dir_inside_root is empty, it means it's a project without an established repository, but
	# rather a set of related scripts. Always call into python script.
	local project_dir_inside_root=${config["dir_inside_root"]}
	if [ -z "$project_dir_inside_root" ]; then
		_dush_project_python_script "$@"
		return
	fi

	# Do different things depending on args passed
	case "$arg" in
		'')       _dush_project_dir_list ;;
		*[!0-9]*) _dush_project_python_script "$@" ;;
		*)        _dush_project_dir_cd "$arg" ;;
	esac
}

_dush_project_dir_list() {
	local project_name=${config["name"]}
	local project_name_friendly=${config["name_friendly"]}
	local project_dir_inside_root=${config["dir_inside_root"]}

	get_branchname() {
        workspace="$1"
        cd "$workspace" 2>/dev/null || {
			echo "(<ERROR>)"
			return
		}
		branch="$(git branch --show-current)"
		if [ -n "$branch" ]; then
			echo "($branch)"
		else
			echo "(FREE from $(git log --format=%cr -1))"
		fi
	}

	echo "$project_name_friendly workspaces:"
	for workspace in $(find $DUSH_WORKSPACE/ -maxdepth 1 -regex ".*/$project_name""[0-9]*$"); do
		branch="$(get_branchname "$workspace/$project_dir_inside_root")"
		echo "    $workspace     $branch"
	done
}

_dush_project_python_script() {
	local project_path=${config["path"]}
	local project_name=${config["name"]}

	local script_name="$project_path/$project_name.py"
	_dush_call_python_script "$script_name" "$@"
}

_dush_project_dir_cd() {
	local index="$1"
	local project_name=${config["name"]}
	local project_dir_inside_root=${config["dir_inside_root"]}

	cd "$DUSH_WORKSPACE/$project_name$index/$project_dir_inside_root" 2>/dev/null && return 0

	if [ "$index" = 1 ]; then
		cd "$DUSH_WORKSPACE/$project_name/$project_dir_inside_root" 2>/dev/null && return 0
	fi

	echo "Could not cd"
	return 1
}



# --------------------------------------------------------------------- Utils for reload scripts
dush_generate_bash_completion() {
	declare -n config="dush_project_$1"
	local main_func=${config["main_func"]}
	local project_path=${config["path"]}

	local cache_file="$project_path/commands.cache"
	if [ -f "$cache_file" ]; then
		read -r args < "$cache_file"
	else
		args="$($main_func list -- -q | tr -d '\n' | tr -d '\r')"
		printf "$args\n" > "$cache_file"
	fi

	complete -W "$args" "$project_name"
}

_dush_load_python_script_as_bash_function() {
	local script_file="$1"

	local script_name="${script_file%.*}"
	local script_name="$(basename "$script_name")"
	local function_definition="$script_name() { _dush_call_python_script \"$script_file\" \"\$@\" ; }"
	eval "$function_definition"
}

dush_load_python_scripts_as_bash_functions() {
	declare -n config="dush_project_$1"
	local project_path=${config["path"]}

	while read -r script_file; do
		_dush_load_python_script_as_bash_function "$script_file"
	done <<< "$(find $project_path -name "*.py")"
}

dush_load_bash_scripts() {
	declare -n config="dush_project_$1"
	local project_path=${config["path"]}

	export IS_LINUX="$(uname -a | grep -cv "Linux")"
	local forbidden_dir="$([ "$IS_LINUX" = 0 ] && echo windows || echo linux)"

	for file in $(find "$project_path" -name "*.sh" -not -path "*/$forbidden_dir/*" -not -path "*/runnable/*" -not -path "*/main.sh" | sort); do
		. "$file"
	done
}



# --------------------------------------------------------------------- Other utils
_dush_call_python_script() {
	local script_name="$1"
	shift
	PYTHONPATH=$DUSH_PATH $DUSH_PYTHON_COMMAND "$script_name" "$@"
}

_dush_call_lazy_reload() {
	# Each project can have a reload function. In this function it usually loads shell completion
	# for the project. This takes relatively a lot of time when there are multiple project, since
	# it has to call python main script.
	#
	# To optimize this, we call reload function lazily upon first call to project_main. The code
	# looks a bit complicated, because we basically have to pass a reference to the varable info
	# whether reload was already called or not. In bash it is done by passing the name of the
	# variable and initializing it with some "local -n" magic. We also pass a callback to the
	# project-specific reload function as a string. This can be simply called as usual.

	if [ "${config["is_loaded"]}" = 0 ]; then
		config["is_loaded"]="1"

		reload_func=${config["reload_func"]}
		$reload_func
	fi
}
