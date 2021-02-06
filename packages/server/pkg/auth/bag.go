package auth

import (
	"reflect"
	"strconv"
	"strings"

	"github.com/rotisserie/eris"
)

func UnmarshalBag(data string, dest interface{}) error {
	destRef := reflect.ValueOf(dest).Elem()
	fieldCount := destRef.NumField()
	fields := make(map[string]reflect.Value, fieldCount)

	for idx := 0; idx < fieldCount; idx++ {
		fields[destRef.Type().Field(idx).Name] = destRef.Field(idx)
	}

	var err error
	dataLen := len(data)
	state := 0
	lastPos := 0
	key := ""
	for idx := 0; idx < dataLen; idx++ {
		switch state {
		case 0:
			if data[idx] == '=' {
				key = data[lastPos:idx]
				lastPos = idx + 1
				state = 1
			}
			break
		case 1:
			if data[idx] == '#' {
				ref, ok := fields[key]
				if !ok {
					return eris.Errorf("invalid field %s found", key)
				}

				var value interface{}
				switch ref.Type().Name() {
				case "int":
					value, err = strconv.Atoi(data[lastPos:idx])
					if err != nil {
						return eris.Wrapf(err, "failed to parse field %s", key)
					}
				case "string":
					value = data[lastPos:idx]
				default:
					return eris.Errorf("field %s has unsupported type %s", key, ref.Type().Name())
				}

				ref.Set(reflect.ValueOf(value))
				lastPos = idx + 1
				state = 0
			}
			break
		default:
			panic("invalid state")
		}
	}

	switch state {
	case 0:
		if lastPos != dataLen {
			panic("corrupted state")
		}
		break
	case 1:
		if lastPos < dataLen {
			panic("corrupted end")
		} else if lastPos > dataLen {
			panic("corrupted last pos")
		}
		break
	}

	return nil
}

func MarshalBag(src interface{}) (string, error) {
	srcRef := reflect.ValueOf(src)
	fieldCount := srcRef.NumField()

	builder := strings.Builder{}
	for idx := 0; idx < fieldCount; idx++ {
		key := srcRef.Type().Field(idx).Name
		value := srcRef.Field(idx).String()

		builder.WriteString(key)
		builder.WriteRune('=')
		builder.WriteString(value)
		builder.WriteRune('#')
	}

	return builder.String(), nil
}
