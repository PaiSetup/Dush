#!/bin/sh

. $DUSH_PATH/framework/frontend.bash

yuview_reload() {
	dush_create_bash_completion_script yuview
}

dush_init_project yuview yuview yuview_reload
