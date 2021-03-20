import { FileRef } from '@api/mod';

export interface RefImageProps {
  src?: FileRef;
}
export default function RefImage(props: RefImageProps): React.ReactElement | null {
  return props.src ? <img src={'https://api.client.fsnebula.org/ref/' + props.src.fileid} /> : null;
}
