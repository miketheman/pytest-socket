.PHONY: all clean install test mutmut dist testrelease release

INSTALL_STAMP := .install.stamp
UV := $(shell command -v uv 2> /dev/null)
PYTEST_FLAGS :=

all: test

clean:
	@find . -name \*.pyc -delete
	@find . -name __pycache__ -delete
	@rm -fr $(INSTALL_STAMP) .cache/ .coverage .pytest_cache/ *.egg-info/ dist/ htmlcov/ .venv/

install: $(INSTALL_STAMP)
uv.lock:
$(INSTALL_STAMP): pyproject.toml uv.lock
ifndef UV
	$(error "uv is not available, please install it first.")
endif
	@uv sync
	@touch $(INSTALL_STAMP)

test: $(INSTALL_STAMP)
	@uv run coverage run -m pytest $(PYTEST_FLAGS) ; uv run coverage report --show-missing

mutmut: $(INSTALL_STAMP)
	@uv run mutmut run
	@results=$$(uv run mutmut results); \
	echo "$$results"; \
	bad=$$(echo "$$results" | grep -E "__mutmut_[0-9]+:" | grep -v ": segfault$$" || true); \
	if [ -n "$$bad" ]; then \
		echo "ERROR: non-killed mutants detected (see above)"; exit 1; \
	fi
	@# Segfaults are tolerated: mutating the plugin's own pytest hooks crashes
	@# the inner pytest that mutmut runs (non-deterministic, esp. free-threaded),
	@# so they can't be "killed" by a test. Any other non-killed status fails.

dist: clean $(INSTALL_STAMP)
	@uv build

testrelease: dist
	# Requires config in ~/.pypirc or similar
	@uv publish --publish-url https://test.pypi.org/legacy/

release: dist
	@uv publish
