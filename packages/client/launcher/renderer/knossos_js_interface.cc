#include "renderer/knossos_js_interface.h"

#include <cstdlib>
#include <stdexcept>
#include <vector>

#include "include/cef_base.h"
#include "include/cef_frame.h"
#include "include/cef_process_message.h"
#include "include/cef_v8.h"
#include "include/wrapper/cef_helpers.h"

class KnossosApiV8Handler: public CefV8Handler {
  bool Execute(const CefString& name,
                                  CefRefPtr<CefV8Value> object,
                                  const CefV8ValueList& arguments,
                                  CefRefPtr<CefV8Value>& retval,
                                  CefString& exception) OVERRIDE
  {
    if (name == "knShowDevTools") {
      if (arguments.size() == 0) {
        CefRefPtr<CefProcessMessage> msg = CefProcessMessage::Create("knDevToolsRequest");
        CefRefPtr<CefV8Context> ctx = CefV8Context::GetCurrentContext();

        ctx->GetFrame()->SendProcessMessage(PID_BROWSER, msg);

        retval = CefV8Value::CreateBool(true);
        return true;
      }
    }

    return false;
  };

private:
  IMPLEMENT_REFCOUNTING(KnossosApiV8Handler);
};

void KnossosJsInterface::Init() {
  std::string extensionCode =
      "var knShowDevTools = null;"
      "var knAddMessageListener = null;"
      "var knRemoveMessageListener = null;"
      "var knDeliverMessage = null;"
      "(function() {"
      "  const _listeners = [];"
      "  knShowDevTools = function() {"
      "    native function knShowDevTools();"
      "    return knShowDevTools();"
      "  };"
      "  knAddMessageListener = function (cb) {"
      "    _listeners.push(cb);"
      "  };"
      "  knRemoveMessageListener = function (cb) {"
      "    const idx = _listeners.indexOf(cb);"
      "    if (idx > -1) _listeners.splice(idx, 1);"
      "  };"
      "  knDeliverMessage = function (msg) {"
      "    for (const cb of _listeners) {"
      "      try {"
      "        cb(msg);"
      "      } catch(e) {"
      "        console.error(e);"
      "      }"
      "    }"
      "  };"
      "})();";

  CefRegisterExtension("kninterface", extensionCode, new KnossosApiV8Handler());
}

class SimpleBufferReleaser : public CefV8ArrayBufferReleaseCallback {
  public:
  virtual void ReleaseBuffer(void* buffer) OVERRIDE {
    std::free(buffer);
  }

  private:
  IMPLEMENT_REFCOUNTING(SimpleBufferReleaser);
};

bool KnossosJsInterface::ProcessMessage(CefRefPtr<CefBrowser> browser,
                                        CefRefPtr<CefFrame> frame,
                                        CefProcessId source_process,
                                        CefRefPtr<CefProcessMessage> message
) {
  CEF_REQUIRE_RENDERER_THREAD();
  if (message->GetName() == "knJsMessage") {
    auto ctx = frame->GetV8Context();
    ctx->Enter();

    CefV8ValueList args;

    auto data = message->GetArgumentList()->GetBinary(0);
    void* buffer = std::malloc(data->GetSize());
    auto read = data->GetData(buffer, data->GetSize(), 0);
    if (read != data->GetSize()) {
      LOG(ERROR) << "Read only " << read << " of " << data->GetSize() << " bytes in a knJsMessage";
    }

    args.push_back(CefV8Value::CreateArrayBuffer(buffer, data->GetSize(), new SimpleBufferReleaser()));

    ctx->GetGlobal()->GetValue("knDeliverMessage")->ExecuteFunction(nullptr, args);
    ctx->Exit();

    return true;
  }

  return false;
}
