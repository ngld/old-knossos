#include "renderer/knossos_js_interface.h"

#include <cstdlib>
#include <stdexcept>
#include <vector>

#include "include/cef_base.h"
#include "include/cef_frame.h"
#include "include/cef_process_message.h"
#include "include/cef_v8.h"
#include "include/cef_values.h"
#include "include/internal/cef_ptr.h"
#include "include/internal/cef_types.h"
#include "include/wrapper/cef_helpers.h"

class KnossosApiV8Handler : public CefV8Handler {
  bool Execute(const CefString &name, CefRefPtr<CefV8Value> object,
               const CefV8ValueList &arguments, CefRefPtr<CefV8Value> &retval,
               CefString &exception) OVERRIDE {
    if (name == "knShowDevTools") {
      if (arguments.size() == 0) {
        CefRefPtr<CefProcessMessage> msg =
            CefProcessMessage::Create("knDevToolsRequest");
        CefRefPtr<CefV8Context> ctx = CefV8Context::GetCurrentContext();

        ctx->GetFrame()->SendProcessMessage(PID_BROWSER, msg);

        retval = CefV8Value::CreateBool(true);
        return true;
      }
    } else if (name == "knOpenFile") {
      if (arguments.size() == 5) {
        // knOpenFile(title, default_filename, accepted, resolve, reject);
        CefRefPtr<CefProcessMessage> msg =
            CefProcessMessage::Create("knOpenFileRequest");
        CefRefPtr<CefV8Context> ctx = CefV8Context::GetCurrentContext();

        auto accepted = CefListValue::Create();
        if (arguments[2]->IsArray()) {
          for (int i = 0; i < arguments[2]->GetArrayLength(); i++) {
            auto item = arguments[2]->GetValue(i);
            if (item == nullptr)
              return false;

            accepted->SetString(i, item->GetStringValue());
          }
        }

        auto promise = new KnJsPromise;
        promise->resolve = arguments[3];
        promise->reject = arguments[4];

        auto args = msg->GetArgumentList();
        args->SetString(0, arguments[0]->GetStringValue());
        args->SetString(1, arguments[1]->GetStringValue());
        args->SetList(2, accepted);
        args->SetInt(3, KnossosJsInterface::RegisterPromise(promise));

        ctx->GetFrame()->SendProcessMessage(PID_BROWSER, msg);
        return true;
      }
    } else if (name == "knOpenFolder") {
      if (arguments.size() == 4) {
        // knOpenFolder(title, default_folder, resolve, reject);
        auto promise = new KnJsPromise;
        promise->resolve = arguments[2];
        promise->reject = arguments[3];

        CefRefPtr<CefProcessMessage> msg =
            CefProcessMessage::Create("knOpenFolderRequest");
        CefRefPtr<CefV8Context> ctx = CefV8Context::GetCurrentContext();

        auto args = msg->GetArgumentList();
        args->SetString(0, arguments[0]->GetStringValue());
        args->SetString(1, arguments[1]->GetStringValue());
        args->SetInt(2, KnossosJsInterface::RegisterPromise(promise));

        ctx->GetFrame()->SendProcessMessage(PID_BROWSER, msg);
        return true;
      }
    } else if (name == "knSaveFile") {
      if (arguments.size() == 5) {
        // knSaveFile(title, default_filename, accepted, resolve, reject);

        CefRefPtr<CefProcessMessage> msg =
            CefProcessMessage::Create("knSaveFileRequest");
        CefRefPtr<CefV8Context> ctx = CefV8Context::GetCurrentContext();

        auto accepted = CefListValue::Create();
        if (arguments[2]->IsArray()) {
          for (int i = 0; i < arguments[2]->GetArrayLength(); i++) {
            auto item = arguments[2]->GetValue(i);
            if (item == nullptr)
              return false;

            accepted->SetString(i, item->GetStringValue());
          }
        }

        auto promise = new KnJsPromise;
        promise->resolve = arguments[3];
        promise->reject = arguments[4];

        auto args = msg->GetArgumentList();
        args->SetString(0, arguments[0]->GetStringValue());
        args->SetString(1, arguments[1]->GetStringValue());
        args->SetList(2, accepted);
        args->SetInt(3, KnossosJsInterface::RegisterPromise(promise));

        ctx->GetFrame()->SendProcessMessage(PID_BROWSER, msg);
        return true;
      }
    }

    return false;
  };

private:
  IMPLEMENT_REFCOUNTING(KnossosApiV8Handler);
};

class SimpleBufferReleaser : public CefV8ArrayBufferReleaseCallback {
public:
  virtual void ReleaseBuffer(void *buffer) OVERRIDE { std::free(buffer); }

private:
  IMPLEMENT_REFCOUNTING(SimpleBufferReleaser);
};

int KnossosJsInterface::next_promise_id_ = 0;
std::map<int, KnJsPromise *> KnossosJsInterface::pending_promises_;

void KnossosJsInterface::Init() {
  std::string extensionCode =
      "var knShowDevTools = null;"
      "var knAddMessageListener = null;"
      "var knRemoveMessageListener = null;"
      "var knDeliverMessage = null;"
      "var knOpenFile = null;"
      "var knOpenFolder = null;"
      "var knSaveFile = null;"
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
      "  knOpenFile = function (title, default_filename, accepted) {"
      "    native function knOpenFile();"
      "    return new Promise((resolve, reject) => {"
      "      try {"
      "        knOpenFile(title, default_filename, accepted, resolve, reject);"
      "      } catch(e) {"
      "        reject(e);"
      "      }"
      "    });"
      "  };"
      "  knOpenFolder = function (title, default_folder) {"
      "    native function knOpenFolder();"
      "    return new Promise((resolve, reject) => {"
      "      try {"
      "        knOpenFolder(title, default_folder, resolve, reject);"
      "      } catch(e) {"
      "        reject(e);"
      "      }"
      "    });"
      "  };"
      "  knSaveFile = function (title, default_filename, accepted) {"
      "    native function knSaveFile();"
      "    return new Promise((resolve, reject) => {"
      "      try {"
      "        knSaveFile(title, default_filename, accepted, resolve, reject);"
      "      } catch(e) {"
      "        reject(e);"
      "      }"
      "    });"
      "  };"
      "})();";

  CefRegisterExtension("kninterface", extensionCode, new KnossosApiV8Handler());
}

int KnossosJsInterface::RegisterPromise(KnJsPromise *promise) {
  auto id = next_promise_id_++;
  pending_promises_[id] = promise;
  return id;
}

bool KnossosJsInterface::ProcessMessage(CefRefPtr<CefBrowser> browser,
                                        CefRefPtr<CefFrame> frame,
                                        CefProcessId source_process,
                                        CefRefPtr<CefProcessMessage> message) {
  CEF_REQUIRE_RENDERER_THREAD();
  if (message->GetName() == "knJsMessage") {
    auto ctx = frame->GetV8Context();
    ctx->Enter();

    CefV8ValueList args;

    auto data = message->GetArgumentList()->GetBinary(0);
    void *buffer = std::malloc(data->GetSize());
    auto read = data->GetData(buffer, data->GetSize(), 0);
    if (read != data->GetSize()) {
      LOG(ERROR) << "Read only " << read << " of " << data->GetSize()
                 << " bytes in a knJsMessage";
    }

    args.push_back(CefV8Value::CreateArrayBuffer(buffer, data->GetSize(),
                                                 new SimpleBufferReleaser()));

    ctx->GetGlobal()
        ->GetValue("knDeliverMessage")
        ->ExecuteFunction(nullptr, args);
    ctx->Exit();

    return true;
  } else if (message->GetName() == "knResolvePromiseWithString") {
    auto args = message->GetArgumentList();
    auto promise = pending_promises_.find(args->GetInt(0));
    if (promise == pending_promises_.end()) {
      LOG(ERROR) << "Tried to resolve missing promise " << args->GetInt(0);
      return true;
    }

    auto ctx = frame->GetV8Context();
    ctx->Enter();

    CefV8ValueList js_args;
    js_args.push_back(CefV8Value::CreateString(args->GetString(1)));

    promise->second->resolve->ExecuteFunction(nullptr, js_args);
    ctx->Exit();

    // free the promise
    delete promise->second;
    pending_promises_.erase(args->GetInt(0));

    return true;
  } else if (message->GetName() == "knResolvePromiseWithStringArray") {
    auto args = message->GetArgumentList();
    auto promise = pending_promises_.find(args->GetInt(0));
    if (promise == pending_promises_.end()) {
      LOG(ERROR) << "Tried to resolve missing promise " << args->GetInt(0);
      return true;
    }

    auto ctx = frame->GetV8Context();
    ctx->Enter();

    auto results = args->GetList(1);
    auto js_results = CefV8Value::CreateArray(results->GetSize());
    for (size_t i = 0; i < results->GetSize(); i++) {
      js_results->SetValue(i, CefV8Value::CreateString(results->GetString(i)));
    }

    CefV8ValueList js_args;
    js_args.push_back(js_results);

    promise->second->resolve->ExecuteFunction(nullptr, js_args);
    ctx->Exit();

    // free the promise
    delete promise->second;
    pending_promises_.erase(args->GetInt(0));

    return true;
  } else if (message->GetName() == "knRejectPromiseWithError") {
    auto args = message->GetArgumentList();
    auto promise = pending_promises_.find(args->GetInt(0));
    if (promise == pending_promises_.end()) {
      LOG(ERROR) << "Tried to reject missing promise " << args->GetInt(0)
                 << " with " << args->GetString(1);
      return true;
    }

    auto ctx = frame->GetV8Context();
    ctx->Enter();

    CefRefPtr<CefV8Value> error;
    CefRefPtr<CefV8Exception> exception;

    auto prop_attr = CefV8Value::PropertyAttribute::V8_PROPERTY_ATTRIBUTE_NONE;

    ctx->GetGlobal()->SetValue(
        "_error_msg", CefV8Value::CreateString(args->GetString(1)), prop_attr);
    ctx->Eval("return new Error(_error_msg);", "", 1, error, exception);
    ctx->GetGlobal()->SetValue("_error_msg", CefV8Value::CreateUndefined(),
                               prop_attr);

    if (exception.get()) {
      LOG(ERROR) << "Failed to create error: " << exception->GetMessage();
    } else {
      CefV8ValueList js_args;
      js_args.push_back(error);

      promise->second->reject->ExecuteFunction(nullptr, js_args);
    }

    ctx->Exit();

    // free promise
    delete promise->second;
    pending_promises_.erase(args->GetInt(0));

    return true;
  }

  return false;
}
