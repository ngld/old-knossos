
#include "browser/knossos_resource_handler.h"
#include "dynknossos.h"

KnossosResourceHandler::KnossosResourceHandler(): res_handle(0) {}

KnossosResourceHandler::~KnossosResourceHandler() {
  if (res_handle != 0) {
    KnossosFree(res_handle);
  }
}

void KnossosResourceHandler::Cancel()
{
}

void KnossosResourceHandler::GetResponseHeaders(CefRefPtr<CefResponse> response,
                                                int64& response_length,
                                                CefString& redirectUrl)
{
  response->SetHeaderByName("Access-Control-Allow-Origin", "*", true);
}

bool KnossosResourceHandler::Open(CefRefPtr<CefRequest> request,
                                  bool &handle_request,
                                  CefRefPtr<CefCallback> callback)
{
  std::string url = request->GetURL();
  handle_request = true;

  res_handle = KnossosShouldHandleResource((char*)url.c_str(), url.size());
  if (res_handle) {
    return true;
  }

  return false;
}

bool KnossosResourceHandler::Read(void* data_out,
                                  int bytes_to_read,
                                  int& bytes_read,
                                  CefRefPtr<CefResourceReadCallback> callback)
{
  return false;
}
