#!/bin/sh

. $DUSH_PATH/utils/bash_utils.bash
bashies_project_subdir="bashies"

bashies_reload() {
	load_bash_scripts "$bashies_project_subdir"
	load_python_scripts_as_bash_functions "$bashies_project_subdir"
}
bashies_reload
