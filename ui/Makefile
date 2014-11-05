../knossos/ui/%.py: %.ui
	@echo "Compiling $<..."
	@pyside-uic -o $@ $<
	@sed -i -e 's#from PySide import#from ..qt import#' -e '/^import resources.*/ d' $@
