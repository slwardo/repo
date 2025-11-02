#!/bin/zsh
#no no no
case $- in
    *i*) ;;
      *) return;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoredupes

export LD_LIBRARY_PATH=/opt/homebrew/lib:$LD_LIBRARY_PATH
export RUBY_CONFIGURE_OPTS=--with-opt-dir=/opt/homebrew
export LDFLAGS="-L/opt/homebrew/opt/curl/lib"
export CPPFLAGS="-I/opt/homebrew/opt/curl/include"
# append to the history file, don't overwrite it
export PATH=/opt/homebrew/bin:$PATH

# Global
export PATH=$HOME/bin:$PATH
export EDITOR=vi

# Homebrew
export HOMEBREW_NO_ANALYTICS=1

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
export HISTSIZE=10000
export HISTFILESIZE=20000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
export HISTIGNORE="&:ls:[bf]g:exit"
export CLICOLOR=1
export LSCOLORS=GxFxCxDxBxegedabagaced
#PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
#PS1='wardo:\W$ '
PROMPT='%~ %# '

# some more ls aliases
bu () { cp ~/.zprofile ~/.backup/'zprofile'-`date +%Y%m%d%H%M`.backup ;  }
alias editzprofile='vi $HOME/.zprofile'
alias editzpro='bu && editzprofile'
alias s='source $HOME/.zprofile'
#alias curl="/opt/homebrew/opt/curl/bin/curl"
#alias openssl="/opt/homebrew/opt/openssl/bin/openssl\@3.0"

alias subl="/Applications/Sublime\ Text.app/Contents/SharedSupport/bin/subl"

alias ll='ls -alh'                                                     # List files
alias llr='ls -alhr'                                                   # List files (reverse)
h() { history | grep "$1"; }                                           # Shorthand for `history` with added grepping


# Utilities
alias getsshkey="pbcopy < ~/.ssh/id_rsa.pub"               # Copy SSH key to the keyboard
disk-usage() { du -hs "$@" | sort -nr; }                  # List disk usage of all the files in a directory (use -hr to sort on server)
mktar() { tar cvzf "${1%%/}.tar.gz"  "${1%%/}/"; }    # Creates a *.tar.gz archive of a file or folder
mkzip() { zip -r "${1%%/}.zip" "$1" ; }               # Create a *.zip archive of a file or folder


# Navigation Shortcuts
alias home='clear && cd ~ && ll'                                     # Home directory
alias downloads='clear && cd ~/Downloads && ll'                      # Downloads directory


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


#dirsize - finds directory sizes and lists them for the current directory
dirsize ()
{
du -shx * .[a-zA-Z0-9_]* 2> /dev/null | \
egrep '^ *[0-9.]*[MG]' | sort -n > /tmp/list
egrep '^ *[0-9.]*M' /tmp/list
egrep '^ *[0-9.]*G' /tmp/list
rm -rf /tmp/list
}


# For gcloud to reauth with SK.
export SK_SIGNING_PLUGIN=gnubbyagent
export GOOGLE_AUTH_WEBAUTHN_PLUGIN=gcloudwebauthn

ECP_CERTIFICATE_CONFIG_FILE_PATH=/etc/certificate_config.json
if groups | grep -q -w ecp-config-deployment ; then
  export CLOUDSDK_CONTEXT_AWARE_CERTIFICATE_CONFIG_FILE_PATH="${ECP_CERTIFICATE_CONFIG_FILE_PATH}"
  export GOOGLE_API_CERTIFICATE_CONFIG="${ECP_CERTIFICATE_CONFIG_FILE_PATH}"
fi
if groups | grep -q -w gcloud-mTLS-deployment ; then
  export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=true
fi


export BASH_SILENCE_DEPRECATION_WARNING=1

complete -C /opt/homebrew/bin/terraform terraform

# The next line updates PATH for the Google Cloud SDK.
#if [ -f '/Users/stefanward/google-cloud-sdk/path.bash.inc' ]; then . '/Users/stefanward/google-cloud-sdk/path.bash.inc'; fi

# The next line enables shell command completion for gcloud.
#if [ -f '/Users/stefanward/google-cloud-sdk/completion.bash.inc' ]; then . '/Users/stefanward/google-cloud-sdk/completion.bash.inc'; fi
export PATH="/opt/homebrew/opt/curl/bin:$PATH"
