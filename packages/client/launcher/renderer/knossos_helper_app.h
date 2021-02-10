#ifndef KNOSSOS_KNOSSOS_RENDERER_HANDLER
#define KNOSSOS_KNOSSOS_RENDERER_HANDLER

#include "include/cef_app.h"

class KnossosHelperApp : public CefApp, public CefRenderProcessHandler
{
public:
  KnossosHelperApp();

  virtual CefRefPtr<CefRenderProcessHandler> GetRenderProcessHandler() OVERRIDE {
    return this;
  };

  virtual void OnWebKitInitialized() OVERRIDE;

private:
  // Include the default reference counting implementation.
  IMPLEMENT_REFCOUNTING(KnossosHelperApp);
};

#endif /* KNOSSOS_KNOSSOS_RENDERER_HANDLER */
