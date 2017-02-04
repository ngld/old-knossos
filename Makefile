## Copyright 2015 Knossos authors, see NOTICE file
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

RCC_FILES = \
	$(shell find html -type f) \
	$(shell find ui -name '*.png' -or -name '*.jpg' -or -name '*.css') \
	knossos/data/hlp.png
UI_FILES = $(wildcard ui/*.ui)
SED_I = sed -i
PYTHON ?= python
PY3 := $(realpath $(shell which python3))
ifneq ($(PY3),)
	# Default to python3 by default
	PYTHON = $(PY3)
endif

UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
	SED_I = sed -i ''
endif

.PHONY: run debug dist clean resources ui

run: resources ui
	$(PYTHON) -m knossos

debug: resources ui
	KN_DEBUG=1 $(PYTHON) -m knossos

dist: resources ui
	$(PYTHON) setup.py sdist bdist_wheel

clean:
	@# Delete all python bytecode files
	find knossos -type f \( -name '*.pyc' -or -name '*.pyo' \) -delete
	rm -f knossos/data/resources.rcc

	@# Keep the __init__.py but delete all other *.py files in knossos/ui.
	find knossos/ui -name '__init__.py' -or -name '*.py' -delete

resources: knossos/data/resources.rcc

ui: $(patsubst ui/%.ui,knossos/ui/%.py,$(UI_FILES))

knossos/data/resources.rcc: $(RCC_FILES)
	@./tools/common/run_helper.sh compile_resources

knossos/ui/%.py: ui/%.ui
	$(PYTHON) -mPyQt5.uic.pyuic -o $@ $<
	@$(SED_I) -e 's#from PyQt5 import#from ..qt import#' -e '/^import resources.*/d' -e '/setContentsMargins(0, 0, 0, 0)/d' $@
