
#include "browser/knossos_resource_handler.h"

#include <cstring>
#include <string>
#include "dynknossos.h"
#include "include/cef_request.h"

KnossosResourceHandler::KnossosResourceHandler(): pos(0),
  kn_response(0) {}

KnossosResourceHandler::~KnossosResourceHandler() {
  if (kn_response != 0) {
    KnossosFreeKnossosResponse(kn_response);
  }
}

void KnossosResourceHandler::Cancel()
{
  if (kn_response != 0) {
    KnossosFreeKnossosResponse(kn_response);
    kn_response = 0;
  }
}

void KnossosResourceHandler::GetResponseHeaders(CefRefPtr<CefResponse> response,
                                                int64& response_length,
                                                CefString& redirectUrl)
{
  response->SetHeaderByName("Access-Control-Allow-Origin", "*", true);

  if (kn_response == 0) {
    response->SetStatus(500);
    response_length = 0;
    return;
  }

  if (kn_response->status_code != 0) {
    response->SetStatus(kn_response->status_code);
  }

  for (int i = 0; i < kn_response->header_count; i++) {
    auto hdr = kn_response->headers[i];
    CefString header(std::string(hdr.header_name, hdr.header_len));
    CefString value(std::string(hdr.value, hdr.value_len));

    response->SetHeaderByName(header, value, true);
  }

  if (kn_response->response_length > 0) {
    response_length = kn_response->response_length;
  } else {
    response_length = -1;
  }
}

bool KnossosResourceHandler::Open(CefRefPtr<CefRequest> request,
                                  bool &handle_request,
                                  CefRefPtr<CefCallback> callback)
{
  std::string url = request->GetURL();
  handle_request = true;
  if (request->GetMethod() == "OPTIONS") {
    return true;
  }

  if (request->GetMethod() == "POST") {
    auto post_data = request->GetPostData();
    if (post_data == nullptr) {
      LOG(WARNING) << "Invalid request " << url << ": Empty request";
      // SetStringResponse(400, "Empty request");
      kn_response = 0;
      return true;
    }

    CefPostData::ElementVector body;
    post_data->GetElements(body);

    if (body.size() > 1) {
      LOG(ERROR) << "Expected at most one body part on request " << url << " but found " << body.size() << "!";
      // SetStringResponse(400, "More than one body part");
      kn_response = 0;
      return true;
    }

    size_t body_size = 0;
    void* body_contents = 0;
    if (body.size() > 0) {
      body_size = body[0]->GetBytesCount();
      body_contents = malloc(body_size);
      auto bytes_read = body[0]->GetBytes(body_size, body_contents);

      if (bytes_read != body_size) {
        LOG(WARNING) << "Incomplete body read for request " << url << ": Read " << bytes_read << " out of " << body_size << ".";
      }
    }

    // FIXME This call can block which shouldn't happen on the IO thread. Instead, we should post to a background thread,
    // and call the passed callback once we're done.
    kn_response = KnossosHandleRequest((char*)url.c_str(), (int)url.size(), body_contents, (int)body_size);
    if (body_contents != 0) {
      std::free(body_contents);
    }

    if (kn_response != 0) {
      return true;
    }

    LOG(WARNING) << "Invalid request " << url << ": No handler found";
    // SetStringResponse(404, "No handler found");
    kn_response = 0;
    return true;
  } else if(url.find("https://api.client.fsnebula.org/ref/") == 0) {
    kn_response = KnossosHandleRequest((char*)url.c_str(), (int)url.size(), nullptr, 0);
    if (kn_response != 0) {
      return true;
    }

    LOG(WARNING) << "Invalid request " << url << ": No handler found";
    // SetStringResponse(404, "No handler found");
    kn_response = 0;
    return true;
  }

  LOG(WARNING) << "Invalid request " << url << ": Invalid method";
  // SetStringResponse(400, "Invalid method");
  kn_response = 0;
  return true;
}

bool KnossosResourceHandler::Read(void* data_out,
                                  int bytes_to_read,
                                  int& bytes_read,
                                  CefRefPtr<CefResourceReadCallback> callback)
{
  if (kn_response != 0) {
    int to_read = std::min(bytes_to_read, (int)(kn_response->response_length - pos));
    std::memcpy(data_out, (char*)kn_response->response_data + pos, to_read);

    pos += to_read;
    bytes_read = to_read;
    LOG(INFO) << "[" << bytes_to_read << ";" << to_read << "  # " << pos << "/" << kn_response->response_length << "]";
    return to_read > 0;
  }
  return false;
}
