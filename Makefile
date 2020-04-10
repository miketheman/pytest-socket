.PHONY: all clean poetry test dist testrelease release

POETRY := $(shell command -v poetry 2> /dev/null)

all: test

clean:
	@find . -name \*.pyc -delete
	@find . -name __pycache__ -delete
	@rm -fr .cache/ .coverage .pytest_cache/ *.egg-info/ dist/ htmlcov/

poetry.lock pytest_socket.egg-info/ :
ifndef POETRY
	$(error "poetry is not available, please install it first.")
endif
	@poetry install

test: pytest_socket.egg-info/
	@poetry run pytest

dist: clean poetry.lock
	@poetry build

testrelease: dist
	# Requires config: `repositories.testpypi.url = "https://test.pypi.org/simple"`
	@poetry publish --repository testpypi

release: dist
	@poetry publish
