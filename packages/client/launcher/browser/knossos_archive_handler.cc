#include "browser/knossos_archive_handler.h"

#include <cstring>
#include "include/internal/cef_string.h"

KnossosArchiveHandler::KnossosArchiveHandler(CefRefPtr<KnossosArchive> archive, int prefix_length) :
  _archive(archive), _prefix_length(prefix_length), _pos(0), _res_size(0), _res_data(0) {}

KnossosArchiveHandler::~KnossosArchiveHandler() {
  if (_res_data != 0) {
    std::free(_res_data);
    _res_data = 0;
  }
}

void KnossosArchiveHandler::Cancel() {
  if (_res_data != 0) {
    std::free(_res_data);
    _res_data = 0;
  }
}

bool KnossosArchiveHandler::Open(CefRefPtr<CefRequest> request, bool& handle_request, CefRefPtr<CefCallback> callback) {
  handle_request = true;

  CefString url = request->GetURL();
  if (url.length() < (size_t)_prefix_length) {
    LOG(ERROR) << "Request for URL " << url << " is shorter than the expected prefix length (" << _prefix_length << ")";
    return false;
  }

  std::string name = url;
  name = name.substr(_prefix_length);

  _archive->ReadEntry(name, _res_size, &_res_data);

  LOG(INFO) << "Loaded " << url << " of size " << _res_size << " from archive";

  if (_res_size == 0) {
    return false;
  }

  std::string ext = name.substr(name.size() - 4, 4);
  if (ext == ".css") {
    _mime = "text/css";
  } else if (ext == ".png") {
    _mime = "image/png";
  } else if (ext == ".jpg") {
    _mime = "image/jpeg";
  } else if (ext == ".gif") {
    _mime = "image/gif";
  } else if (ext == ".txt") {
    _mime = "text/plain";
  } else {
    if (name.substr(name.size() - 3, 3) == ".js") {
      _mime = "text/javascript";
    } else if (name.substr(name.size() - 5, 5) == ".html") {
      _mime = "text/html";
    } else if (name.substr(name.size() - 5, 5) == ".json") {
      _mime = "application/json";
    } else {
      _mime = "application/octet-stream";
    }
  }

  return true;
}

void KnossosArchiveHandler::GetResponseHeaders(CefRefPtr<CefResponse> response, int64& response_length, CefString& redirectUrl) {
  response->SetHeaderByName("Content-Type", CefString(_mime), false);
  response->SetMimeType(CefString(_mime));
  response->SetCharset("utf8");

  response_length = _res_size;
}

bool KnossosArchiveHandler::Read(void* data_out, int bytes_to_read, int& bytes_read, CefRefPtr<CefResourceReadCallback> callback) {
  if (_pos == 0) {
    if (bytes_to_read >= _res_size) {
      // simple case: just copy everything at once
      std::memcpy(data_out, _res_data, _res_size);
      bytes_read = (int)_res_size;

      _pos += _res_size;
      return true;
    }
  } else if (_pos >= (size_t)_res_size) {
    bytes_read = 0;
    return false;
  }

  int to_read = std::min((int)(_res_size - _pos), bytes_to_read);
  std::memcpy(data_out, ((char*)_res_data + _pos), to_read);
  bytes_read = to_read;
  _pos += to_read;
  return true;
}
