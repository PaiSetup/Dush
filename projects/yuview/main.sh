#!/bin/sh

. $DUSH_PATH/utils/bash_utils.bash
yuview_project_subdir="yuview"
yuview_project_name="yuview"
yuview_project_name_friendly="yuview"
yuview_project_dir_inside_root="."
yuview_project_loaded="0"

yuview() {
	project_main "$yuview_project_subdir" "$yuview_project_name" "$yuview_project_name_friendly" "$yuview_project_dir_inside_root" "yuview_project_loaded" "yuview_reload" "$@"
}

yuview_reload() {
	create_bash_completion_script "$yuview_project_name"
	load_bash_scripts "$misc_project_subdir"
}

if [ "$DUSH_ENABLE_AUTOLOAD" = "1" ]; then
	yuview_project_loaded="1"
	yuview_reload
fi
