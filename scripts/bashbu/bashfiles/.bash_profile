# ~/.bash_profile: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoredupes
shopt -s cmdhist
# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
export HISTSIZE=10000
export HISTFILESIZE=20000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize
export HISTIGNORE="&:ls:[bf]g:exit"


# set variable identifying the chroot you work in (used in the prompt below)
#if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
#    debian_chroot=$(cat /etc/debian_chroot)
#fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac


if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
	color_prompt=yes
    else
	color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='wardos-mach:\$ '
else
    PS1='h: \$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias dir='dir --color=auto'
    alias vdir='vdir --color=auto'
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi


# some more ls aliases
alias bashme='vi $HOME/.bash_profile'
alias s='source $HOME/.bash_profile'
alias ll='ls -alh'                                                     # List files
alias llr='ls -alhr'                                                   # List files (reverse)
alias lls='ls -alhS'                                                   # List files by size
alias llsr='ls -alhSr'                                                 # List files by size (reverse)
alias lld='ls -alht'                                                   # List files by date
alias lldr='ls -alhtr'                                                 # List files by date (reverse)
alias lldc='ls -alhtU'                                                 # List files by date created
alias lldcr='ls -alhtUr'                                               # List files by date created (reverse)
h() { history | grep "$1"; }                                           # Shorthand for `history` with added grepping

# This is GOLD for finding out what is taking so much space on your drives!
alias myfiles='cd $HOME/MyFiles'
alias prj='cd $HOME/projects'
alias scripts='cd $HOME/projects/scripts'
alias gitrepo='cd $HOME/projects/github'
alias download='cd $HOME/Downloads'
alias gdrive='cd $HOME/gDrive/MyDrive'

# Utilities
alias getsshkey="pbcopy < ~/.ssh/id_rsa.pub"                        # Copy SSH key to the keyboard
disk-usage() { du -hs "$@" | sort -nr; }                            # List disk usage of all the files in a directory (use -hr to sort on server)
mktar() { tar cvzf "${1%%/}.tar.gz"  "${1%%/}/"; }                  # Creates a *.tar.gz archive of a file or folder
mkzip() { zip -r "${1%%/}.zip" "$1" ; }                             # Create a *.zip archive of a file or folder
bu () { cp $1 ~/.backup/`basename $1`-`date +%Y%m%d%H%M`.backup ; }
alias diskspace='du -S | sort -n -r |more'
alias findy='find . -name'
#alias curl="$HOME/homebrew/opt/curl/bin/curl"
#alias openssl="$HOME/homebrew/opt/openssl/bin/openssl"

# Navigation Shortcuts
alias home='clear && cd ~ && ll'                                     # Home directory
alias downloads='clear && cd ~/Downloads && ll'                      # Downloads directory
alias ..='cl ..'
alias ...='cl ../../'
alias ....='cl ../../../'
alias .....='cl ../../../../'
alias ......='cl ../../../../'
alias .......='cl ../../../../../'
alias ........='cl ../../../../../../'


# Directory and file stuff
alias folders='find . -maxdepth 1 -type d -print | xargs du -sk | sort -rn'    # size (sorted) of only the folders
alias tree="find . -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'"  # List the file structure of the current directory
dirdiff() { diff -u <( ls "$1" | sort)  <( ls "$2" | sort ); }       # Compare the contents of 2 directories
cs() { cd "$@" &&  ls; }                                             # Enter directory and list contents with ls
cl() { cd "$@" && ll; }                                              # Enter directory and list contents with ll
alias perm="stat -f '%Lp'"                                             # View the permissions of a file/dir as a number
alias mkdir='mkdir -pv'                                                # Make parent directories if needed

# Clear a directory
cleardir() {
    while true; do
        read -ep 'Completely clear current directory? [y/N] ' response
        case $response in
            [Yy]* )
                bash -c 'rm -rfv ./*'
                bash -c 'rm -rfv ./.*'
                break;;
            * )
                echo 'Skipped clearing the directory...'
                break;;
        esac
    done
}

#unzip anything
extract () {
     if [ -f $1 ] ; then
         case $1 in
             *.tar.bz2)   tar xjf $1        ;;
             *.tar.gz)    tar xzf $1     ;;
             *.bz2)       bunzip2 $1       ;;
             *.rar)       rar x $1     ;;
             *.gz)        gunzip $1     ;;
             *.tar)       tar xf $1        ;;
             *.tbz2)      tar xjf $1      ;;
             *.tgz)       tar xzf $1       ;;
             *.zip)       unzip $1     ;;
             *.Z)         uncompress $1  ;;
             *.7z)        7z x $1    ;;
             *)           echo "'$1' cannot be extracted via extract()" ;;
         esac
     else
         echo "'$1' is not a valid file"
     fi
}

#netinfo - shows network information for your system
netinfo ()
{
echo "--------------- Network Information ---------------"
/sbin/ifconfig | awk /'inet addr/ {print $2}'
/sbin/ifconfig | awk /'Bcast/ {print $3}'
/sbin/ifconfig | awk /'inet addr/ {print $4}'
/sbin/ifconfig | awk /'HWaddr/ {print $4,$5}'
myip=`lynx -dump -hiddenlinks=ignore -nolist http://checkip.dyndns.org:8245/ | sed '/^$/d; s/^[ ]*//g; s/[ ]*$//g' `
echo "${myip}"
echo "---------------------------------------------------"
}

#dirsize - finds directory sizes and lists them for the current directory
dirsize ()
{
du -shx * .[a-zA-Z0-9_]* 2> /dev/null | \
egrep '^ *[0-9.]*[MG]' | sort -n > /tmp/list
egrep '^ *[0-9.]*M' /tmp/list
egrep '^ *[0-9.]*G' /tmp/list
rm -rf /tmp/list
}

#copy and go to dir
cpg (){
  if [ -d "$2" ];then
    cp $1 $2 && cd $2
  else
    cp $1 $2
  fi
}

#move and go to dir
mvg (){
  if [ -d "$2" ];then
    mv $1 $2 && cd $2
  else
    mv $1 $2
  fi
}

psgrep() {
	if [ ! -z $1 ] ; then
		echo "Grepping for processes matching $1..."
		ps aux | grep $1 | grep -v grep
	else
		echo "!! Need name to grep for"
	fi
}
grab() {
	sudo chown -R ${USER} ${1:-.}
}


# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bash_profile and /etc/profile
# sources /etc/bash.bash_profile).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# The next line updates PATH for the Google Cloud SDK.
if [ -f '$HOME/Downloads/google-cloud-sdk/path.bash.inc' ]; then . '/$HOME/Downloads/google-cloud-sdk/path.bash.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '$HOME/Downloads/google-cloud-sdk/completion.bash.inc' ]; then . '$HOME/Downloads/google-cloud-sdk/completion.bash.inc'; fi

