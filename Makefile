RCC_FILES = \
	$(shell find html -type f) \
	$(shell find ui -name '*.png' -or -name '*.jpg' -or -name '*.css') \
	knossos/data/hlp.png
UI_FILES = $(wildcard ui/*.ui)
SED_I = sed -i
PYTHON = python

UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
	SED_I = sed -i ''
endif

run: resources ui
	$(PYTHON) -m knossos

debug: resources ui
	KN_DEBUG=1 $(PYTHON) -m knossos

dist:
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
	pyside-uic -o $@ $<
	@$(SED_I) -e 's#from PySide import#from ..qt import#' -e '/^import resources.*/ d' $@
