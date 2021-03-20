#ifndef KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_DEV_TOOLS
#define KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_DEV_TOOLS

#include "include/cef_browser.h"
#include "include/internal/cef_ptr.h"
#include "include/views/cef_browser_view.h"
#include "include/views/cef_window.h"

class KnossosDevToolsWindowDelegate : public CefWindowDelegate {
public:
  explicit KnossosDevToolsWindowDelegate(CefRefPtr<CefBrowserView> browser_view)
        : browser_view_(browser_view) {}

  void OnWindowCreated(CefRefPtr<CefWindow> window) OVERRIDE;
  void OnWindowDestroyed(CefRefPtr<CefWindow> window) OVERRIDE;

  CefRect GetInitialBounds(CefRefPtr<CefWindow> window) OVERRIDE;
private:
  CefRefPtr<CefBrowserView> browser_view_;

  IMPLEMENT_REFCOUNTING(KnossosDevToolsWindowDelegate);
  DISALLOW_COPY_AND_ASSIGN(KnossosDevToolsWindowDelegate);
};

void KnossosShowDevTools(CefRefPtr<CefBrowser> browser);


#endif /* KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_DEV_TOOLS */
