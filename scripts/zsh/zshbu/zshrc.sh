#.zshrc

#editandbackup
#buzshrc () { cp ~/.zshrc ~/.backup/'zshrc'-`date +%Y%m%d%H%M`.backup ;  }
#alias zshrc='vi $HOME/.zshrc'
#alias edzshrc='buzshrc && zshrc'

#fileactions
alias cp='cp -iv'                             # Preferred 'cp' implementation
alias mv='mv -iv'                             # Preferred 'mv' implementation
alias mkdir='mkdir -pv'                       # Preferred 'mkdir' implementation
alias ll='ls -FGlAhp'                         # Preferred 'ls' implementation
alias llr='ls -FGlAhpr'                         # Preferred 'ls' implementation
alias h='hisory'                              # Preferred 'history' implementation
alias j='jobs -l'                             # Preferred 'jobs' implementation
alias less='less -FSRXc'                      # Preferred 'less' implementation
cd() { builtin cd "$@"; ll; }                 # Always list directory contents upon 'cd'
cdr() { builtin cd "$@"; ll; }                 # Always list directory contents upon 'cd'

#navigation
alias cd..='cd ../'                           # Go back 1 directory level (for fast typers)
alias ..='cd ../'                             # Go back 1 directory level
alias ...='cd ../../'                         # Go back 2 directory levels
alias .3='cd ../../../'                       # Go back 3 directory levels
alias .4='cd ../../../../'                    # Go back 4 directory levels
alias .5='cd ../../../../../'                 # Go back 5 directory levels
alias .6='cd ../../../../../../'              # Go back 6 directory levels
cl() { cd "$@" &&  ll; }                                             # Enter directory and list contents with ls
cr() { cd "$@" && llr; }                                              # Enter directory and list contents with ll
alias root='cd /'
alias home='cd ~'
alias scripts='cd ~/scripts'
alias gitrepo='cd ~/gitrepo'
alias downloads='cd ~/Downloads'
alias bin='cd ~/bin'
alias gdrive='cd ~/Google\ Drive/My\ Drive/'

alias edit='subl'                             # edit:         Opens any file in sublime editor
alias f='open -a Finder ./'                   # f:            Opens current directory in MacOS Finder
alias ~="cd ~"                                # ~:            Go Home
alias c='clear'                               # c:            Clear terminal display

mcd () { mkdir -p "$1" && cd "$1"; }          # mcd:          Makes new Dir and jumps inside
trash () { command mv "$@" ~/.Trash ; }       # trash:        Moves a file to the MacOS trash
ql () { qlmanage -p "$*" >& /dev/null; }      # ql:           Opens any file in MacOS Quicklook Preview
def() { curl -s dict://dict.org/d:$1 | perl -ne 's/\r//; last if /^\.$/; print if /^151/../^250/'; }
lasts () { last | grep -v "^$" | awk '{ print $1 }' | sort -nr | uniq -c; }


# some more ls aliases
alias gocert='gcert'
alias cthn='ssh slwardo-01.c.googlers.com'
alias goct='gocert && cthn'



#   -------------------------------
#   3.  FILE AND FOLDER MANAGEMENT
#   -------------------------------

zipf () { zip -r "$1".zip "$1" ; }          # zipf:         To create a ZIP archive of a folder
alias numFiles='echo $(ls -1 | wc -l)'      # numFiles:     Count of non-hidden files in current dir
alias make1mb='mkfile 1m ./1MB.dat'         # make1mb:      Creates a file of 1mb size (all zeros)
alias make5mb='mkfile 5m ./5MB.dat'         # make5mb:      Creates a file of 5mb size (all zeros)
alias make10mb='mkfile 10m ./10MB.dat'      # make10mb:     Creates a file of 10mb size (all zeros)


#   extract:  Extract most know archives with one command
#   ---------------------------------------------------------
    extract () {
        if [ -f $1 ] ; then
          case $1 in
            *.tar.bz2)   tar xjf $1     ;;
            *.tar.gz)    tar xzf $1     ;;
            *.bz2)       bunzip2 $1     ;;
            *.rar)       unrar e $1     ;;
            *.gz)        gunzip $1      ;;
            *.tar)       tar xf $1      ;;
            *.tbz2)      tar xjf $1     ;;
            *.tgz)       tar xzf $1     ;;
            *.zip)       unzip $1       ;;
            *.Z)         uncompress $1  ;;
            *.7z)        7z x $1        ;;
            *)     echo "'$1' cannot be extracted via extract()" ;;
             esac
         else
             echo "'$1' is not a valid file"
         fi
    }

#   lock: Lock the screen
#   ---------------------------------------------------------
    alias lock='open -a /System/Library/Frameworks/ScreenSaver.framework/Versions/A/Resources/ScreenSaverEngine.app'

#   suspend: Suspend the computer
#   ---------------------------------------------------------
    alias suspend='/System/Library/CoreServices/Menu\ Extras/User.menu/Contents/Resources/CGSession -suspend'

#   ---------------------------
#   4.  SEARCHING
#   ---------------------------

alias qfind="find . -name "                 # qfind:   Quickly search for file
ff () { /usr/bin/find . -name "$@" ; }      # ff:      Find file under the current directory
ffs () { /usr/bin/find . -name "$@"'*' ; }  # ffs:     Find file whose name starts with a given string
ffe () { /usr/bin/find . -name '*'"$@" ; }  # ffe:     Find file whose name ends with a given string

#   spotlight: Search for a file using MacOS Spotlight's metadata
#   -----------------------------------------------------------
    spotlight () { mdfind "kMDItemDisplayName == '$@'wc"; }


#   ---------------------------
#   5.  PROCESS MANAGEMENT
#   ---------------------------

#   findpid: find out the pid of a specified process
#   -----------------------------------------------------
#       Note that the command name can be specified via a regex
#       E.g. findPid '/d$/' finds pids of all processes with names ending in 'd'
#       Without the 'sudo' it will only find processes of the current user
#   -----------------------------------------------------
    findpid () { lsof -t -c "$@" ; }

#   memhogstop, memhogsps:  Find memory hogs
#   -----------------------------------------------------
    alias memhogstop='top -l 1 -o rsize | head -20'
    alias memhogsps='ps wwaxm -o pid,stat,vsize,rss,time,command | head -10'

#   cpuhogs:  Find CPU hogs
#   -----------------------------------------------------
    alias cpuhogs='ps wwaxr -o pid,stat,%cpu,time,command | head -10'

#   topforever:  Continual 'top' listing (every 10 seconds)
#   -----------------------------------------------------
    alias topforever='top -l 9999999 -s 10 -o cpu'

#   ttop:  Recommended 'top' invocation to minimize resources
#   ------------------------------------------------------------
#       Taken from this macosxhints article
#       http://www.macosxhints.com/article.php?story=20060816123853639
#   ------------------------------------------------------------
    alias ttop="top -R -F -s 10 -o rsize"

#   my_ps: List processes owned by my user:
#   ------------------------------------------------------------
    my_ps() { ps $@ -u $USER -o pid,%cpu,%mem,start,time,bsdtime,command ; }
    alias ppu='ps hax -o user | sort | uniq -c'         #Processes Per User



