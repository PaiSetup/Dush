#!/bin/sh

. $DUSH_PATH/framework/frontend.bash

bashies_reload() {
	dush_load_bash_scripts bashies
	dush_load_python_scripts_as_bash_functions bashies
}
dush_init_project bashies "" bashies_reload
