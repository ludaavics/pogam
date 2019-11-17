SPHINXBUILD     = sphinx-build
SOURCEDIR       = docs
BUILDDIR        = docs/_build
GH_PAGES_SOURCE = docs pogam Makefile

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
	@pytest --cov=pogam --cov-branch --verbose

docs-clean:
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)"

docs:
	@make docs-clean
	@$(SPHINXBUILD) -anE -b html "$(SOURCEDIR)" "$(BUILDDIR)"/html

docs-live:
	@make docs-clean
	@sleep 1 && touch ${SOURCEDIR}/*.rst
	@sphinx-autobuild \
		-q \
		-b html \
		-p 0 \
		--open-browser \
		--delay 5 \
		--ignore "*.pdf" \
		--ignore "*.log" \
		$(SOURCEDIR) \
		$(BUILDDIR)/html

docs-tests:
	@$(SPHINXBUILD) -nEWT -b dummy "$(SOURCEDIR)" "$(BUILDDIR)"

docs-help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)"

integration:
	@make tests
	@make docs-tests

gh-pages:
	@git checkout gh-pages
	@git reset --hard HEAD
	@ rm -rf ./_sources ./_static
	@git checkout master $(GH_PAGES_SOURCE)
	@git reset HEAD
	@make docs
	@mv -fv ${BUILDDIR}/html/* ./
	@rm -rf $(GH_PAGES_SOURCE) ${BUILDDIR}
	@git add -A
	@git commit -m "Generated gh-pages for `git log master -1 --pretty=short --abbrev-commit`"; git push $$(git rev-parse --abbrev-ref gh-pages@{upstream} | grep -o '[^//]*' | head -1) gh-pages ; git checkout master

.PHONY: help Makefile docs tests
