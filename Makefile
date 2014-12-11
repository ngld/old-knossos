RCC_FILES = $(shell find html -type f) $(shell find ui -name '*.png' -or -name '*.jpg' -or -name '*.css') knossos/data/hlp.png
UI_FILES = $(patsubst ui/%.ui,knossos/ui/%.py,$(wildcard ui/*.ui))
SED_I = sed -i

UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
	SED_I = sed -i ''
endif

dist:
	python setup.py sdist bdist_wheel

clean:
	find knossos -type f -name '*.pyc' -delete -or -name '*.pyo' -delete
	rm -f knossos/data/resources.rcc
	rm -f knossos/ui/*.py{,c,o}

run: resources ui
	python -m knossos

resources: knossos/data/resources.rcc

ui: $(UI_FILES)

knossos/data/resources.rcc: $(RCC_FILES)
	@./tools/common/run_helper.sh compile_resources

knossos/ui/%.py: ui/%.ui
	@echo "Compiling $<..."
	@pyside-uic -o $@ $<
	@$(SED_I) -e 's#from PySide import#from ..qt import#' -e '/^import resources.*/ d' $@
