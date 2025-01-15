#!/bin/sh

. $DUSH_PATH/framework/frontend.bash

yuview_reload() {
	dush_generate_bash_completion yuview
}

dush_init_project yuview yuview yuview_reload
