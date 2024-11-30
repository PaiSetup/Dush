#/bin/bash

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



# --------------------------------------------------------------------- project_main and its subroutines
project_main() {
	project_subdir="$1"
	project_name="$2"
	project_name_friendly="$3"
	project_dir_inside_root="$4"
	project_loaded_name="$5"
	reload_func="$6"
	arg="$7"

	# Shift 6 times, so that "$@" contains user specified arguments
	shift 6;

	# Lazy reload
	call_lazy_reload "$project_loaded_name" "$reload_func"

	# If project_dir_inside_root is empty, it means it's a project without an established repository, but
	# rather a set of related scripts. Always call into python script.
	if [ -z "$project_dir_inside_root" ]; then
		project_python_script "$project_subdir" "$project_name" "$@"
		return
	fi

	# Do different things depending on args passed
	case "$arg" in
		'')       project_dir_list "$project_name" "$project_name_friendly" "$project_dir_inside_root" ;;
		*[!0-9]*) project_python_script "$project_subdir" "$project_name" "$@" ;;
		*)        project_dir_cd "$project_name" "$arg" "$project_dir_inside_root" ;;
	esac
}

project_dir_list() {
	project_name="$1"
	project_name_friendly="$2"
	project_dir_inside_root="$3"

	get_branchname() {
        workspace="$1"
        cd "$workspace" 2>/dev/null
		if [ $? != 0 ]; then
			echo "(<ERROR>)"
			return
		fi
		branch="$(git branch --show-current)"
		if [ -n "$branch" ]; then
			echo "($branch)"
		else
			echo "(FREE from $(git log --format=%cr -1))"
		fi
	}

	echo "$project_name_friendly workspaces:"
	for workspace in $(find $DUSH_WORKSPACE/ -maxdepth 1 -regex ".*/$project_name[0-9]*$"); do
		branch="$(get_branchname "$workspace/$project_dir_inside_root")"
		echo "    $workspace     $branch"
	done
}

project_python_script() {
	local project_subdir="$1"
	local project_name="$2"

	# Shift 2 times, so that "$@" contains user specified arguments
	shift 2;

	local script_name="$DUSH_PATH/projects/$project_subdir/$project_name.py"
	call_python_script "$script_name" "$@"
}

project_dir_cd() {
	project_name="$1"
	index="$2"
	project_dir_inside_root="$3"

	cd "$DUSH_WORKSPACE/$project_name$index/$project_dir_inside_root"
}



# --------------------------------------------------------------------- Utils for reload scripts
create_bash_completion_script() {
	local project_name="$1"

	args="$($project_name list -- -q | tr -d '\n' | tr -d '\r')"
	complete -W "$args" "$project_name"
}

load_python_script_as_bash_function() {
	local script_file="$1"

	local script_name="${script_file%.*}"
	local script_name="$(basename "$script_name")"
	local function_definition="$script_name() { call_python_script \"$script_file\" \"\$@\" ; }"
	eval "$function_definition"
}

load_python_scripts_as_bash_functions() {
	local project_subdir="$1"
	local project_dir="$DUSH_PATH/projects/$project_subdir/"

	while read -r script_file; do
		load_python_script_as_bash_function "$script_file"
	done <<< "$(find $project_dir -name "*.py")"
}

load_bash_scripts() {
	local project_subdir="$1"
	local project_dir="$DUSH_PATH/projects/$project_subdir/"

	export IS_LINUX="$(uname -a | grep -cv "Linux")"
	local forbidden_dir="$([ "$IS_LINUX" = 0 ] && echo windows || echo linux)"

	for file in $(find "$project_dir" -name "*.sh" -not -path "*/$forbidden_dir/*" -not -path "*/runnable/*" -not -path "*/main.sh" | sort); do
		. "$file"
	done
}



# --------------------------------------------------------------------- Other utils
call_python_script() {
	local script_name="$1"
	shift
	PYTHONPATH=$DUSH_PATH $DUSH_PYTHON_COMMAND "$script_name" "$@"
}

call_lazy_reload() {
	# Each project can have a reload function. In this function it usually loads shell completion
	# for the project. This takes relatively a lot of time when there are multiple project, since
	# it has to call python main script.
	#
	# To optimize this, we call reload function lazily upon first call to project_main. The code
	# looks a bit complicated, because we basically have to pass a reference to the varable info
	# whether reload was already called or not. In bash it is done by passing the name of the
	# variable and initializing it with some "local -n" magic. We also pass a callback to the
	# project-specific reload function as a string. This can be simply called as usual.

	local project_loaded_name="$1"
	local reload_func="$2"

	local -n project_loaded="$project_loaded_name"
	if [ "$project_loaded" = 0 ]; then
		project_loaded=1
		$reload_func
	fi
}
