package archives

import (
	"encoding/binary"
	"io"
	"os"
	"time"

	"github.com/rotisserie/eris"
)

// VpFile contains the metadata for a file entry
type VpFile struct {
	timestamp time.Time
	offset    int32
	size      int32
}

// VpFolder contains an index of the available sub-folders and files
type VpFolder struct {
	folders map[string]*VpFolder
	files   map[string]*VpFile
}

// VpWriter can write .vp archives
type VpWriter struct {
	hdl      *os.File
	root     *VpFolder
	dirStack []*VpFolder
	current  *VpFolder
	buffer   []byte
}

// NewVpWriter creates a new VpWriter instance and opens it for writing
func NewVpWriter(filename string) (*VpWriter, error) {
	hdl, err := os.Create(filename)
	if err != nil {
		return nil, err
	}

	root := new(VpFolder)
	root.folders = map[string]*VpFolder{}
	root.files = map[string]*VpFile{}

	dirStack := make([]*VpFolder, 1)
	dirStack[0] = root

	// skip the header which consists of 4 chars and 3 int32s
	_, err = hdl.Seek(int64(4+12), io.SeekStart)
	if err != nil {
		hdl.Close()
		return nil, err
	}

	return &VpWriter{
		hdl:      hdl,
		root:     root,
		dirStack: dirStack,
		current:  root,
		buffer:   make([]byte, 4096),
	}, nil
}

// OpenDirectory creates a new directory entry. Anything created until the next CloseDirectory() call will be created
// inside this directory.
func (w *VpWriter) OpenDirectory(dirname string) error {
	dir := new(VpFolder)
	dir.folders = map[string]*VpFolder{}
	dir.files = map[string]*VpFile{}

	w.current.folders[dirname] = dir
	w.dirStack = append(w.dirStack, dir)
	w.current = dir

	return nil
}

// CloseDirectory closes the directory that was last opened
func (w *VpWriter) CloseDirectory() error {
	stackLen := len(w.dirStack)
	if stackLen < 2 {
		return eris.New("No directory left on stack")
	}

	w.dirStack = w.dirStack[:stackLen-1]
	w.current = w.dirStack[stackLen-2]
	return nil
}

// WriteFile creates a new file in the current archive directory
func (w *VpWriter) WriteFile(filename string, reader io.Reader) error {
	item := new(VpFile)
	offset, err := w.hdl.Seek(0, io.SeekCurrent)
	if err != nil {
		return err
	}

	item.offset = int32(offset)
	size, err := io.CopyBuffer(w.hdl, reader, w.buffer)
	if err != nil {
		return err
	}

	item.size = int32(size)
	item.timestamp = time.Now()
	w.current.files[filename] = item

	return nil
}

// Close writes the central index and closes the archive
func (w *VpWriter) Close() error {
	if len(w.dirStack) != 1 {
		w.hdl.Close()
		return eris.New("Open directories left over!")
	}

	items := int32(0)
	buffer := make([]byte, 44)
	tocOffset, err := w.hdl.Seek(0, io.SeekCurrent)
	if err != nil {
		w.hdl.Close()
		return err
	}
	err = writeDirectoryEntries(w.root, w.hdl, &items, buffer)
	if err != nil {
		w.hdl.Close()
		return err
	}

	_, err = w.hdl.Seek(0, io.SeekStart)
	if err != nil {
		w.hdl.Close()
		return err
	}

	buffer[0] = 'V'
	buffer[1] = 'P'
	buffer[2] = 'V'
	buffer[3] = 'P'
	binary.LittleEndian.PutUint32(buffer[4:8], 2)
	binary.LittleEndian.PutUint32(buffer[8:12], uint32(tocOffset))
	binary.LittleEndian.PutUint32(buffer[12:16], uint32(items))

	_, err = w.hdl.Write(buffer[:16])
	if err != nil {
		w.hdl.Close()
		return err
	}
	err = w.hdl.Close()
	if err != nil {
		return err
	}

	return nil
}

func writeDirectoryEntries(folder *VpFolder, hdl *os.File, items *int32, buffer []byte) error {
	for name, folder := range folder.folders {
		// offset
		binary.LittleEndian.PutUint32(buffer[:4], 0)
		// size
		binary.LittleEndian.PutUint32(buffer[4:8], 0)
		// name
		nameLen := len(name)
		for idx := 0; idx < 32; idx++ {
			if idx >= nameLen {
				buffer[8+idx] = byte(0)
			} else {
				buffer[8+idx] = byte(name[idx])
			}
		}

		// timestamp
		binary.LittleEndian.PutUint32(buffer[40:44], 0)

		_, err := hdl.Write(buffer)
		if err != nil {
			return err
		}
		err = writeDirectoryEntries(folder, hdl, items, buffer)
		if err != nil {
			return err
		}

		// offset
		binary.LittleEndian.PutUint32(buffer[:4], 0)
		// size
		binary.LittleEndian.PutUint32(buffer[4:8], 0)
		// name
		buffer[8] = '.'
		buffer[9] = '.'
		for idx := 10; idx < 40; idx++ {
			buffer[idx] = 0
		}

		// timestamp
		binary.LittleEndian.PutUint32(buffer[40:44], 0)
		_, err = hdl.Write(buffer)
		if err != nil {
			return err
		}
	}

	for name, file := range folder.files {
		// offset
		binary.LittleEndian.PutUint32(buffer[:4], uint32(file.offset))
		// size
		binary.LittleEndian.PutUint32(buffer[4:8], uint32(file.size))
		// name
		nameLen := len(name)
		for idx := 0; idx < 32; idx++ {
			if idx >= nameLen {
				buffer[8+idx] = 0
			} else {
				buffer[8+idx] = name[idx]
			}
		}

		// timestamp
		binary.LittleEndian.PutUint32(buffer[40:44], uint32(file.timestamp.Unix()))
		_, err := hdl.Write(buffer)
		if err != nil {
			return err
		}
	}

	*items += int32(len(folder.folders)*2 + len(folder.files))
	return nil
}
