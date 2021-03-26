#ifndef KNOSSOS_KNOSSOS_JS_INTERFACE
#define KNOSSOS_KNOSSOS_JS_INTERFACE

#include <vector>
#include <map>

#include "include/base/cef_lock.h"
#include "include/cef_v8.h"

typedef struct {
  CefRefPtr<CefV8Value> resolve;
  CefRefPtr<CefV8Value> reject;
} KnJsPromise;

class KnossosJsInterface
{
public:
  static void Init();
  static bool ProcessMessage(CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame, CefProcessId source_process, CefRefPtr<CefProcessMessage> message);

  static int RegisterPromise(KnJsPromise* promise);
private:
  static int next_promise_id_;
  static std::map<int, KnJsPromise*> pending_promises_;
};

#endif /* KNOSSOS_KNOSSOS_JS_INTERFACE */
