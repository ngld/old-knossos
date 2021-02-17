#ifndef KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_ARCHIVE_HANDLER
#define KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_ARCHIVE_HANDLER

#include "include/cef_resource_request_handler.h"

#include "browser/knossos_archive.h"

class KnossosArchiveHandler : public CefResourceRequestHandler,
                               public CefResourceHandler {
  public:
	KnossosArchiveHandler(CefRefPtr<KnossosArchive> archive, int prefix_length);
  ~KnossosArchiveHandler();

  // CefResourceRequestHandler methods:
  virtual CefRefPtr<CefResourceHandler> GetResourceHandler(CefRefPtr<CefBrowser> browser,
    CefRefPtr<CefFrame> frame,
    CefRefPtr<CefRequest> request) OVERRIDE {
    return this;
  }

  // CefResourceHandler methods:
  virtual void Cancel() OVERRIDE;
  virtual bool Open(CefRefPtr<CefRequest> request, bool& handle_request, CefRefPtr<CefCallback> callback) OVERRIDE;
  virtual void GetResponseHeaders(CefRefPtr<CefResponse> response, int64& response_length, CefString& redirectUrl) OVERRIDE;
  virtual bool Read(void* data_out, int bytes_to_read, int& bytes_read, CefRefPtr<CefResourceReadCallback> callback) OVERRIDE;

private:
  CefRefPtr<KnossosArchive> _archive;
  int _prefix_length;

  std::string _mime;
  size_t _pos;
  int32_t _res_size;
  void *_res_data;

IMPLEMENT_REFCOUNTING(KnossosArchiveHandler);
};

#endif /* KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_ARCHIVE_HANDLER */
