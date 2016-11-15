SHELL := /bin/bash

upload:
	python setup.py sdist upload -r pypi
