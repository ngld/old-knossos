#include "renderer/knossos_js_interface.h"

bool KnossosJsInterface::Execute(const CefString& name,
                                 CefRefPtr<CefV8Value> object,
                                 const CefV8ValueList& arguments,
                                 CefRefPtr<CefV8Value>& retval,
                                 CefString& exception)
{
  if (name == "knShowDevTools") {
    if (arguments.size() == 0) {
      CefRefPtr<CefV8Context> ctx = CefV8Context::GetCurrentContext();
      CefRefPtr<CefProcessMessage> msg = CefProcessMessage::Create("knDevToolsRequest");

      ctx->GetFrame()->SendProcessMessage(PID_BROWSER, msg);
      return true;
    }
  }

  return false;
};

void KnossosJsInterface::Init() {
  std::string extensionCode =
      "var knShowDevTools = null;"
      "(function() {"
      "  knShowDevTools = function() {"
      "    native function knShowDevTools();"
      "    return knShowDevTools();"
      "  };"
      "})();";

  CefRefPtr<CefV8Handler> handler = new KnossosJsInterface();
  CefRegisterExtension("kninterface", extensionCode, handler);
}
