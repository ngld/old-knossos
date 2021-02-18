package pkg

import (
	"encoding/binary"
	"io"
	"os"

	"github.com/andybalholm/brotli"
	"github.com/rotisserie/eris"
)

// KarFile contains the metadata for a file entry
type KarFile struct {
	offset  int32
	size    int32
	decSize int32
}

// KarFolder contains an index of the available sub-folders and files
type KarFolder struct {
	folders map[string]*KarFolder
	files   map[string]*KarFile
}

// KarWriter can write . Kar archives
type KarWriter struct {
	hdl      *os.File
	root     *KarFolder
	dirStack []*KarFolder
	current  *KarFolder
	buffer   []byte
}

// NewKarWriter creates a new KarWriter instance and opens it for writing
func NewKarWriter(filename string) (*KarWriter, error) {
	hdl, err := os.Create(filename)
	if err != nil {
		return nil, err
	}

	root := new(KarFolder)
	root.folders = map[string]*KarFolder{}
	root.files = map[string]*KarFile{}

	dirStack := make([]*KarFolder, 1)
	dirStack[0] = root

	// skip the header which consists of 4 chars and 3 int32s
	_, err = hdl.Seek(int64(4+12), io.SeekStart)
	if err != nil {
		hdl.Close()
		return nil, err
	}

	return &KarWriter{
		hdl:      hdl,
		root:     root,
		dirStack: dirStack,
		current:  root,
		buffer:   make([]byte, 4096),
	}, nil
}

// OpenDirectory creates a new directory entry. Anything created until the next CloseDirectory() call will be created
// inside this directory.
func (w *KarWriter) OpenDirectory(dirname string) error {
	dir := new(KarFolder)
	dir.folders = map[string]*KarFolder{}
	dir.files = map[string]*KarFile{}

	w.current.folders[dirname] = dir
	w.dirStack = append(w.dirStack, dir)
	w.current = dir

	return nil
}

// CloseDirectory closes the directory that was last opened
func (w *KarWriter) CloseDirectory() error {
	stackLen := len(w.dirStack)
	if stackLen < 2 {
		return eris.New("No directory left on stack")
	}

	w.dirStack = w.dirStack[:stackLen-1]
	w.current = w.dirStack[stackLen-2]
	return nil
}

// WriteFile creates a new file in the current archive directory
func (w *KarWriter) WriteFile(filename string, reader *os.File) error {
	item := new(KarFile)
	offset, err := w.hdl.Seek(0, io.SeekCurrent)
	if err != nil {
		return err
	}

	item.offset = int32(offset)
	brw := brotli.NewWriterLevel(w.hdl, brotli.BestCompression)

	decSize, err := io.CopyBuffer(brw, reader, w.buffer)
	if err != nil {
		return err
	}

	err = brw.Close()
	if err != nil {
		return err
	}

	newPos, err := w.hdl.Seek(0, io.SeekCurrent)
	if err != nil {
		return err
	}

	item.size = int32(newPos - offset)
	item.decSize = int32(decSize)
	w.current.files[filename] = item

	return nil
}

// Close writes the central index and closes the archive
func (w *KarWriter) Close() error {
	if len(w.dirStack) != 1 {
		w.hdl.Close()
		return eris.New("Open directories left over!")
	}

	items := int32(0)
	buffer := make([]byte, 48)
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

	buffer[0] = 'K'
	buffer[1] = 'N'
	buffer[2] = 'A'
	buffer[3] = 'R'
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

func writeDirectoryEntries(folder *KarFolder, hdl *os.File, items *int32, buffer []byte) error {
	for name, folder := range folder.folders {
		// offset
		binary.LittleEndian.PutUint32(buffer[:4], 0)
		// size
		binary.LittleEndian.PutUint32(buffer[4:8], 0)
		// decSize
		binary.LittleEndian.PutUint32(buffer[8:12], 0)
		// name
		nameLen := len(name)
		binary.LittleEndian.PutUint16(buffer[12:14], uint16(nameLen))
		_, err := hdl.Write(buffer[:14])
		if err != nil {
			return err
		}

		_, err = hdl.WriteString(name)
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
		// decSize
		binary.LittleEndian.PutUint32(buffer[8:12], 0)
		// name
		binary.LittleEndian.PutUint16(buffer[12:14], 2)
		_, err = hdl.Write(buffer[:14])
		if err != nil {
			return err
		}

		_, err = hdl.WriteString("..")
		if err != nil {
			return err
		}
	}

	for name, file := range folder.files {
		// offset
		binary.LittleEndian.PutUint32(buffer[:4], uint32(file.offset))
		// size
		binary.LittleEndian.PutUint32(buffer[4:8], uint32(file.size))
		// decSize
		binary.LittleEndian.PutUint32(buffer[8:12], uint32(file.decSize))
		// name
		nameLen := len(name)
		binary.LittleEndian.PutUint16(buffer[12:14], uint16(nameLen))
		_, err := hdl.Write(buffer[:14])
		if err != nil {
			return err
		}

		_, err = hdl.WriteString(name)
		if err != nil {
			return err
		}
	}

	*items += int32(len(folder.folders)*2 + len(folder.files))
	return nil
}
