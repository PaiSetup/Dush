$date_format = "%Y-%m-%d   %H:%M:%S"
git log --graph --pretty="format:%C(auto,yellow bold)%H %C(auto,green)%<(20,trunc)%aN %C(auto,cyan)%<(45,trunc)%cd %C(auto,reset)%s %C(auto)%d" --date=format:"$date_format" $args
