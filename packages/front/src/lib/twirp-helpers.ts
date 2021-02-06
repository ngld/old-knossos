import { TwirpErrorCode } from '@protobuf-ts/twirp-transport';
import { alert } from './alert';

export function presentTwirpError(code: string | TwirpErrorCode): void {
  if (typeof code === 'string') {
    code = parseInt(code) as TwirpErrorCode;
  }

  switch (code) {
    case TwirpErrorCode.cancelled:
    case TwirpErrorCode.aborted:
      // ignore
      return;
    case TwirpErrorCode.invalid_argument:
    case TwirpErrorCode.malformed:
    case TwirpErrorCode.not_found:
    case TwirpErrorCode.bad_route:
    case TwirpErrorCode.unimplemented:
      alert({
        children: `The server didn't recognize our request. Please clear your cache and reload the page.`,
        confirmButtonText: 'OK',
      });
      return;
    case TwirpErrorCode.deadline_exceeded:
    case TwirpErrorCode.resource_exhausted:
    case TwirpErrorCode.unavailable:
      // transient error
      alert({
        children: `The server ran into an issue while responding. Please try again.`,
        confirmButtonText: 'OK',
      });
      return;
    case TwirpErrorCode.internal:
      // internal error
      alert({
        children: `An internal error occurred. Please try again later.`,
        confirmButtonText: 'OK',
      });
      return;
    case TwirpErrorCode.unknown:
    default:
      // report
      alert({
        children: `An unknown error occured. Please report it and try again.`,
        confirmButtonText: 'OK',
      });
      return;
  }
}
