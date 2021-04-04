import { FileRef } from '@api/mod';

export interface RefImageProps extends React.HTMLAttributes<HTMLImageElement> {
  src?: FileRef;
}
export default function RefImage(props: RefImageProps): React.ReactElement | null {
  return props.src ? (
    <img {...props} src={'https://api.client.fsnebula.org/ref/' + props.src.fileid} />
  ) : null;
}
