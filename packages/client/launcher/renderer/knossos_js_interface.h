#ifndef KNOSSOS_KNOSSOS_JS_INTERFACE
#define KNOSSOS_KNOSSOS_JS_INTERFACE

#include <vector>

#include "include/base/cef_lock.h"
#include "include/cef_v8.h"
#include "include/internal/cef_ptr.h"

class KnossosJsInterface
{
public:
  static void Init();
  static bool ProcessMessage(CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame, CefProcessId source_process, CefRefPtr<CefProcessMessage> message);
};

#endif /* KNOSSOS_KNOSSOS_JS_INTERFACE */
