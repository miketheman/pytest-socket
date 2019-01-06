.PHONY: all clean test

TOX := $(shell command -v tox 2> /dev/null)

all: test

clean:
	@find . -name \*.pyc -name __pycache__ -delete
	@rm -fr .cache/ .coverage* .pytest_cache/ .tox/ *.egg-info/ dist/ htmlcov/

test:
ifndef TOX
	$(error "tox is not available, run `pip install tox`")
endif
	@tox

build: clean
	@python setup.py sdist

testrelease: build
	# Requires a `[pypitest]` section in ~/.pypirc
	@twine upload -r pypitest dist/*

release: build
	@twine upload dist/*
