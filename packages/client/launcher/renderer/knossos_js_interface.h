#ifndef KNOSSOS_KNOSSOS_JS_INTERFACE
#define KNOSSOS_KNOSSOS_JS_INTERFACE

#include "include/cef_v8.h"

class KnossosJsInterface : public CefV8Handler
{
public:
  KnossosJsInterface() {};

  bool Execute(const CefString& name, CefRefPtr<CefV8Value> object, const CefV8ValueList& arguments, CefRefPtr<CefV8Value>& retval, CefString& exception) OVERRIDE;

  static void Init();

private:
  // Include the default reference counting implementation.
  IMPLEMENT_REFCOUNTING(KnossosJsInterface);
};

#endif /* KNOSSOS_KNOSSOS_JS_INTERFACE */
