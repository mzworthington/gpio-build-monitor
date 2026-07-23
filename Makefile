# define the name of the virtual environment directory
VENV := .venv

# default target, when make executed without arguments
all: bootstrap

.PHONY: help all bootstrap venv run test build publish clean serve lint

help:
	@IFS=$$'\n' ; \
    help_lines=(`fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//'`); \
    for help_line in $${help_lines[@]}; do \
        IFS=$$'#' ; \
        help_split=($$help_line) ; \
        help_command=`echo $${help_split[0]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
        help_info=`echo $${help_split[2]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
        printf "%-30s %s\n" $$help_command $$help_info ; \
    done

bootstrap: ## Install Python (via mise) and project dependencies
	./bin/bootstrap

$(VENV)/bin/activate: pyproject.toml
	./bin/bootstrap

venv: $(VENV)/bin/activate ## Alias for bootstrap

serve: bootstrap ## Run the build monitor locally (mock GPIO in debug mode)
	./bin/serve

run: serve ## Alias for serve

lint: bootstrap ## Run ruff linter
	./$(VENV)/bin/ruff check monitor test

test: bootstrap lint ## Run pytest with junit formatting
	./$(VENV)/bin/python -m pytest test/monitor -v --junitxml=junit/test-results.xml

build: bootstrap ## Create sdist and wheel without running tests
	rm -rf build/
	rm -rf dist/
	rm -rf monitor.egg-info/
	./$(VENV)/bin/python -m build --sdist --wheel

publish: test build ## Lint, test, then create distribution packages

clean: ## Remove virtual env, build artifacts, and pyc files
	rm -rf $(VENV)
	rm -rf build/
	rm -rf dist/
	rm -rf monitor.egg-info/
	find . -type f -name '*.pyc' -delete
