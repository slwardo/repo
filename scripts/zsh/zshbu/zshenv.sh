#.zshenv

#   Change Prompt
#   ------------------------------------------------------------
    export O=$(who am i | cut -f 1 -d " ")
    if [ -n "$PS1" ]; then
    PS1="[%1~] $ "
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

# For gcloud to reauth with SK.
export SK_SIGNING_PLUGIN=gnubbyagent
# http://b/353538084
export GOOGLE_AUTH_WEBAUTHN_PLUGIN=gcloudwebauthn

# Enable Enterprise Certificate Proxy for gcloud
ECP_CERTIFICATE_CONFIG_FILE_PATH=/etc/certificate_config.json
if groups | grep -q -w ecp-config-deployment ; then
  export CLOUDSDK_CONTEXT_AWARE_CERTIFICATE_CONFIG_FILE_PATH="${ECP_CERTIFICATE_CONFIG_FILE_PATH}"
  export GOOGLE_API_CERTIFICATE_CONFIG="${ECP_CERTIFICATE_CONFIG_FILE_PATH}"
fi
if groups | grep -q -w gcloud-mTLS-deployment ; then
  export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=true
fi

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/stefanward/gcp/gcp/google-cloud-sdk/path.bash.inc' ]; then . '/Users/stefanward/gcp/gcp/google-cloud-sdk/path.bash.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '/Users/stefanward/gcp/gcp/google-cloud-sdk/completion.bash.inc' ]; then . '/Users/stefanward/gcp/gcp/google-cloud-sdk/completion.bash.inc'; fi



