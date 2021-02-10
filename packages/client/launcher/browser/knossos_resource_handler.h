#ifndef KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_RESOURCE_HANDLER
#define KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_RESOURCE_HANDLER

#include "include/cef_resource_request_handler.h"

class KnossosResourceHandler : public CefResourceRequestHandler,
                               public CefResourceHandler {
  public:
	KnossosResourceHandler();
  ~KnossosResourceHandler();

  // CefResourceRequestHandler methods:
  virtual CefRefPtr<CefResourceHandler> GetResourceHandler(CefRefPtr<CefBrowser> browser,
    CefRefPtr<CefFrame> frame,
    CefRefPtr<CefRequest> request) OVERRIDE {
    return this;
  }

  // CefResourceHandler methods:
  virtual void Cancel() OVERRIDE;
  virtual void GetResponseHeaders(CefRefPtr<CefResponse> response, int64& response_length, CefString& redirectUrl) OVERRIDE;
  virtual bool Open(CefRefPtr<CefRequest> request, bool& handle_request, CefRefPtr<CefCallback> callback) OVERRIDE;
  virtual bool Read(void* data_out, int bytes_to_read, int& bytes_read, CefRefPtr<CefResourceReadCallback> callback) OVERRIDE;

private:
  uint8_t res_handle;

IMPLEMENT_REFCOUNTING(KnossosResourceHandler);
};

#endif /* KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_RESOURCE_HANDLER */
