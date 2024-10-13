.PHONY: help
help: ## Display this help screen.
	@grep -E '^\S.+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-45s\033[0m %s\n", $$1, $$2}'

.PHONY: pyenv-virtualenv
pyenv-virtualenv:  ## Create a virtual environment managed by pyenv-virtualenv.
	pyenv virtualenv timesheets
	echo "timesheets" > .python-version

.PHONY: pyenv-virtualenv-delete
pyenv-virtualenv-delete:  ## Delete a virtual environment managed by pyenv-virtualenv.
	pyenv virtualenv-delete --force `cat .python-version || echo timesheets`
	rm -f .python-version

requirements.txt: requirements.in;
	pip-compile --allow-unsafe --generate-hashes --strip-extras

.PHONY: all clean test
