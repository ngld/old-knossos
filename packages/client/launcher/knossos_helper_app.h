#ifndef KNOSSOS_LAUNCHER_KNOSSOS_HELPER_APP
#define KNOSSOS_LAUNCHER_KNOSSOS_HELPER_APP

#include "include/cef_app.h"

#ifdef OS_MAC

// Implement application-level callbacks for the browser process.
class KnossosHelperApp : public CefApp, public CefRenderProcessHandler {
 public:
  KnossosHelperApp() {};

  // CefApp methods:
  virtual CefRefPtr<CefRenderProcessHandler> GetRenderProcessHandler() OVERRIDE {
    return this;
  };

  // CefRenderProcessHandler methods:
  virtual void OnWebKitInitialized() OVERRIDE;

 private:
  // Include the default reference counting implementation.
  IMPLEMENT_REFCOUNTING(KnossosHelperApp);
};

#endif

#endif /* KNOSSOS_LAUNCHER_KNOSSOS_HELPER_APP */
