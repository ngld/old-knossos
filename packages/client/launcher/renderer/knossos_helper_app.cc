#include "knossos_helper_app.h"

namespace
{
  class KnJsInterface : public CefV8Handler
  {
  public:
    KnJsInterface(){};

    bool Execute(const CefString& name, CefRefPtr<CefV8Value> object, const CefV8ValueList& arguments, CefRefPtr<CefV8Value>& retval, CefString& exception) OVERRIDE {
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

  private:
    // Include the default reference counting implementation.
    IMPLEMENT_REFCOUNTING(KnJsInterface);
  };
} // namespace

KnossosHelperApp::KnossosHelperApp() {}

void KnossosHelperApp::OnWebKitInitialized()
{
  std::string extensionCode =
      "var knShowDevTools = null;"
      "(function() {"
      "  knShowDevTools = function() {"
      "    native function knShowDevTools();"
      "    return knShowDevTools();"
      "  };"
      "})();";

  CefRefPtr<CefV8Handler> handler = new KnJsInterface();
  CefRegisterExtension("kninterface", extensionCode, handler);
}
