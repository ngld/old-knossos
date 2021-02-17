#include "browser/knossos_archive.h"

#include <cstdlib>
#include <fstream>
#include <deque>
#include "include/base/cef_lock.h"
#include "include/base/cef_logging.h"
#include "brotli/decode.h"

KnossosArchive::KnossosArchive() : _hdl(), _items(), _lock() {}

int KnossosArchive::Open(std::string filename) {
  _hdl.open(filename, std::ios::binary);
  if (_hdl.fail()) {
    return 1;
  }

  std::string tmp(4, '\0');
  if (!_hdl.read(&tmp[0], 4)) {
    _hdl.close();
    return 2;
  }

  if (tmp != "VPVP") {
    LOG(ERROR) << "Header " << tmp << " does not match magic string 'VPVP'.";
    _hdl.close();
    return 3;
  }

  int32_t version, index_offset, index_count;
  if (!_hdl.read(reinterpret_cast<char*>(&version), sizeof version)) {
    _hdl.close();
    return 2;
  }
  if (!_hdl.read(reinterpret_cast<char*>(&index_offset), sizeof index_offset)) {
    _hdl.close();
    return 2;
  }
  if (!_hdl.read(reinterpret_cast<char*>(&index_count), sizeof index_count)) {
    _hdl.close();
    return 2;
  }

  _hdl.seekg(index_offset);
  std::deque<std::string> path_stack;

  for (int i = 0; i < index_count; i++) {
    int32_t offset, size, dec_size, timestamp;
    char raw_name[32];

    if (!_hdl.read(reinterpret_cast<char*>(&offset), sizeof offset)) {
      _hdl.close();
      return 4;
    }
    if (!_hdl.read(reinterpret_cast<char*>(&size), sizeof size)) {
      _hdl.close();
      return 4;
    }
    if (!_hdl.read(reinterpret_cast<char*>(&dec_size), sizeof dec_size)) {
      _hdl.close();
      return 4;
    }
    if (!_hdl.read(raw_name, 32)) {
      _hdl.close();
      return 4;
    }
    if (!_hdl.read(reinterpret_cast<char*>(&timestamp), sizeof timestamp)) {
      _hdl.close();
      return 4;
    }

    int name_len = 0;
    for (int a = 0; a < 32; a++) {
      if (raw_name[a] == 0) {
        name_len = a;
        break;
      }
    }
    std::string name(raw_name, name_len);

    if (timestamp == 0) {
      if (size != 0) {
        LOG(ERROR) << "Invalid directory entry \"" << name << "\"!";
        continue;
      }

      if (name == "..") {
        path_stack.pop_back();
      } else {
        path_stack.push_back(name);
      }
    } else {
      std::string full_path("");
      for (std::string element : path_stack) {
        full_path += element;
        full_path += "/";
      }

      full_path += name;

      DLOG(INFO) << "Found: \"" << full_path << "\" [" << size << "," << dec_size << "]";

      auto item = &_items[full_path];
      item->size = size;
      item->dec_size = dec_size;
      item->offset = offset;
    }
  }

  LOG(INFO) << "Found " << _items.size() << " files in " << filename;
  return 0;
}

void KnossosArchive::ReadEntry(std::string name, int32_t &size, void **data) {
  base::AutoLock mutex(_lock);
  auto item = _items.find(name);
  if (item == _items.end()) {
    LOG(ERROR) << "Tried to access \"" << name << "\" but couldn't find it (" << _items.size() << " items present)";
    size = 0;
    return;
  }

  *data = std::malloc(item->second.size);
  _hdl.seekg(item->second.offset);
  if (_hdl.fail()) {
    LOG(ERROR) << "Error while seeking to " << name;
    std::free(*data);
    *data = 0;
    size = 0;
    return;
  }

  if (!_hdl.read(reinterpret_cast<char*>(*data), item->second.size)) {
    LOG(ERROR) << "Error while reading " << name << " from archive";
    std::free(*data);
    *data = 0;
    size = 0;
    return;
  }

  if (item->second.dec_size > 0) {
    size_t dec_size = item->second.dec_size;
    void* dec_data = std::malloc(dec_size);
    LOG(INFO) << "Decompressing " << name << " from " << item->second.size << " to " << dec_size;
    auto result = BrotliDecoderDecompress(item->second.size, (uint8_t*)*data, &dec_size, (uint8_t*)dec_data);
    if (result != BROTLI_DECODER_RESULT_SUCCESS) {
      LOG(ERROR) << "Error while decompressing " << name << " from archive";
      std::free(dec_data);
    } else {
      // Move dec_data to data and free the compressed data
      std::free(*data);
      *data = dec_data;
      size = (int32_t)dec_size;
    }
  } else {
    size = item->second.size;
  }
}

void KnossosArchive::Close() {
  _items.clear();
  _hdl.close();
}
