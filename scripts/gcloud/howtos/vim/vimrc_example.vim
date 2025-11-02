
if v:progname =~? "evim"
  finish
endif

source $VIMRUNTIME/defaults.vim

if has("vms")
  set nobackup		
else
  set backup		
  if has('persistent_undo')
    set undofile	
  endif
endif

if &t_Co > 2 || has("gui_running")
  
  set hlsearch
endif


augroup vimrcEx
  au!

  autocmd FileType text setlocal textwidth=78
augroup END


set background=dark
colorscheme base16-railscasts

highlight clear SignColumn
highlight VertSplit    ctermbg=236
highlight ColorColumn  ctermbg=237
highlight LineNr       ctermbg=236 ctermfg=240
highlight CursorLineNr ctermbg=236 ctermfg=240
highlight CursorLine   ctermbg=236
highlight StatusLineNC ctermbg=238 ctermfg=0
highlight StatusLine   ctermbg=240 ctermfg=12
highlight IncSearch    ctermbg=3   ctermfg=1
highlight Search       ctermbg=1   ctermfg=3
highlight Visual       ctermbg=3   ctermfg=0
highlight Pmenu        ctermbg=240 ctermfg=12
highlight PmenuSel     ctermbg=3   ctermfg=1
highlight SpellBad     ctermbg=0   ctermfg=1


if has('syntax') && has('eval')
  packadd! matchit
endif
