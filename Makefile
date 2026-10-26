PACKAGE=fips
PYTHON=python3
VENV=.venv
LOGO="https://github.com/eudoxys/.github/blob/main/eudoxys_banner.png?raw=true"
LINK="https://www.eudoxys.com/"

all: docs test

$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip

# pdoc documents fips/__init__.py and its public submodules; private
# modules (fips._data, fips._tests) are skipped. Used by deploy-pages.yaml.
docs: $(VENV)
	$(VENV)/bin/pip install --upgrade pdoc . -r requirements.txt
	$(VENV)/bin/pdoc $(PACKAGE)/__init__.py -o $@ --logo $(LOGO) --logo-link $(LINK) --math --mermaid

test: $(VENV)
	$(VENV)/bin/pip install -e . pytest
	$(VENV)/bin/pytest

clean:
	rm -rf docs

.PHONY: all docs test clean
