SPHINXBUILD     = sphinx-build
SOURCEDIR       = docs/source
BUILDDIR        = docs/build
GH_PAGES_SOURCE = docs/source yogam Makefile

OSFLAG 				:=
ifeq ($(OS),Windows_NT)
	OSFLAG += win
else
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Linux)
		OSFLAG += linux
	endif
	ifeq ($(UNAME_S),Darwin)
		OSFLAG += macos
	endif
endif

init:
	@conda env create --file .ci/environment-$(strip $(OSFLAG)).yml
	@ln -s ../../.ci/pre-commit .git/hooks/pre-commit

tests:
	@pytest --cov=yogam --cov-branch --verbose

.PHONY: help Makefile docs tests
