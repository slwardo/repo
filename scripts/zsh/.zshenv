
#editandbackup
#buzshenv () { cp ~/.zshenv ~/.backup/'zshenv'-`date +%Y%m%d%H%M`.backup ;  }
#alias vizshenv='vi $HOME/.zshenv'
#alias zshenv='buzshenv && vizshenv'

#   Change Prompt
#   ------------------------------------------------------------
    export O=$(who am i | cut -f 1 -d " ")
    if [ -n "$PS1" ]; then
#    PS1='\:h\$ '
#PS1="[%~%# ] $ " 
PS1="[%~] $ " 
    fi

#   Set Paths
#   ------------------------------------------------------------
    export PATH="$PATH:/usr/local/bin/"
    export PATH="/usr/local/git/bin:/sw/bin/:/usr/local/bin:/usr/local/:/usr/local/sbin:/usr/local/mysql/bin:$PATH"

#   Set Default Editor (change 'Nano' to the editor of your choice)
#   ------------------------------------------------------------
    export EDITOR=/usr/bin/vi

#   Set default blocksize for ls, df, du
#   from this: http://hints.macworld.com/comment.php?mode=view&cid=24491
#   ------------------------------------------------------------
    export BLOCKSIZE=1k

#   Add color to terminal
#   (this is all commented out as I use Mac Terminal Profiles)
#   from http://osxdaily.com/2012/02/21/add-color-to-the-terminal-in-mac-os-x/
#   ------------------------------------------------------------
   export CLICOLOR=1
   export LSCOLORS=ExFxBxDxCxegedabagacad

