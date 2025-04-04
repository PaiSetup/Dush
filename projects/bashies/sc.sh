#!/bin/sh
sc() (
    shellcheck --exclude=SC2155,SC1090,SC2044 "$@" 
)
scc() (
    seek_for_regular_scripts() {
        find $DUSH_PATH $PAI_SETUP_ROOT -type f                                                 \
          \( -name "*.sh" -o -name "*.bash" \)                                                  \
          -not -path "$PAI_SETUP_ROOT/build/*"
    }
    seek_for_dotfiles_scripts() {
        find ~/.profile ~/.bashrc ~/.bash_profile ~/.xinitrc 2>/dev/null
    }
    (seek_for_regular_scripts ; seek_for_dotfiles_scripts) |  xargs -l1 shellcheck -e 2086,2181,2038,2009,2068,2046,2155,2044,1090,1091,2059,2015,2207
)