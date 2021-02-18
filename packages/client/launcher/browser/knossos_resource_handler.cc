
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

  response_length = kn_response->response_length;
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
      SetStringResponse(400, "Empty request");
      return true;
    }

    CefPostData::ElementVector body;
    post_data->GetElements(body);

    if (body.size() != 1) {
      LOG(ERROR) << "Expected one body part on request " << url << " but found " << body.size() << "!";
      SetStringResponse(400, "Not exactly one body part");
      return true;
    }

    size_t body_size = body[0]->GetBytesCount();
    void* body_contents = std::malloc(body_size);
    auto bytes_read = body[0]->GetBytes(body_size, body_contents);

    if (bytes_read != body_size) {
      LOG(WARNING) << "Incomplete body read for request " << url << ": Read " << bytes_read << " out of " << body_size << ".";
    }

    kn_response = KnossosHandleRequest((char*)url.c_str(), url.size(), body_contents, body_size);
    std::free(body_contents);

    if (kn_response != 0) {
      return true;
    }

    LOG(WARNING) << "Invalid request " << url << ": No handler found";
    SetStringResponse(404, "No handler found");
    return true;
  }

  LOG(WARNING) << "Invalid request " << url << ": Invalid method";
  SetStringResponse(400, "Invalid method");
  return true;
}

bool KnossosResourceHandler::Read(void* data_out,
                                  int bytes_to_read,
                                  int& bytes_read,
                                  CefRefPtr<CefResourceReadCallback> callback)
{
  if (kn_response != 0) {
    if (pos == 0 && (size_t)bytes_to_read >= kn_response->response_length) {
      // simple fast path
      std::memcpy(data_out, kn_response->response_data, kn_response->response_length);
      bytes_read = kn_response->response_length;
      pos = kn_response->response_length;
      return true;
    } else {
      int to_read = std::min(bytes_to_read, (int)(kn_response->response_length - pos));
      std::memcpy(data_out, (char*)kn_response->response_data + pos, to_read);

      pos += to_read;
      bytes_read = to_read;
      LOG(INFO) << "[" << bytes_to_read << ";" << to_read << "  # " << pos << "/" << kn_response->response_length << "]";
      return to_read > 0;
    }
  }
  return false;
}

void KnossosResourceHandler::SetStringResponse(int status, std::string message) {
  auto response = new KnossosResponse;
  response->header_count = 1;
  response->headers = new KnossosHeader[1];

  std::string hdr("Content-Type");
  std::string value("text/plain");

  response->headers[0].header_name = new char[hdr.length() + 1];
  response->headers[0].header_len = hdr.length();
  hdr.copy(response->headers[0].header_name, hdr.length());

  response->headers[0].value = new char[value.length() + 1];
  response->headers[0].value_len = value.length();
  value.copy(response->headers[0].value, value.length());

  response->status_code = status;
  response->response_data = new char[message.length() + 1];
  response->response_length = message.length();
  message.copy((char*)response->response_data, message.length());

  kn_response = response;
}
