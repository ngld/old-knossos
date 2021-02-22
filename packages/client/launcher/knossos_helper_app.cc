#include "knossos_helper_app.h"

#include "renderer/knossos_js_interface.h"

#ifdef OS_MAC

// Keep in sync with knossos_app.cc
bool KnossosHelperApp::OnProcessMessageReceived(CefRefPtr<CefBrowser> browser,
                                                CefRefPtr<CefFrame> frame,
                                                CefProcessId source_process,
                                                CefRefPtr<CefProcessMessage> message
) {
  return KnossosJsInterface::ProcessMessage(browser, frame, source_process, message);
}

// Keep in sync with knossos_app.cc
void KnossosHelperApp::OnWebKitInitialized()
{
  KnossosJsInterface::Init();
}

#endif
