# pfh 8/4/24 - dependency bug, need to split the makefile into 'creates files'
# and 'processes and deploys files' stages.  This is the first stage.

.PHONY: all
.DELETE_ON_ERROR:

SITE_LIST    := tgn wcl

