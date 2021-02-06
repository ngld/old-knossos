import { createContext, useContext } from 'react';
import { model, Model, prop, registerRootStore } from 'mobx-keystone';
import { RpcError, RpcOptions, UnaryCall } from '@protobuf-ts/runtime-rpc';
import { TwirpFetchTransport } from '@protobuf-ts/twirp-transport';
import { Toaster, IToaster } from '@blueprintjs/core';
import { NebulaClient } from '@api/service';
import { presentTwirpError } from './twirp-helpers';
import { User } from '../state/user';

type TwirpHandler<I extends object, O extends object> = (
  input: I,
  options?: RpcOptions,
) => UnaryCall<I, O>;


@model('nebula/GlobalState')
export class GlobalState extends Model({
  user: prop<User | undefined>(),
}) {
  // @ts-expect-error TypeScript can't know that onInit() is called before we can access this
  client: NebulaClient;
  // @ts-expect-error See above
  toaster: IToaster;

  onInit() {
    this.toaster = Toaster.create({});
    this.client = new NebulaClient(
      new TwirpFetchTransport({
        baseUrl: '/twirp',
        deadline: process.env.NODE_ENV === 'production' ? 10000 : 1000,
        interceptors: [
          {
            interceptUnary: (next, method, input, options) => {
              const token = this.user?.token;
              if (token && token !== '') {
                if (!options.meta) options.meta = {};
                options.meta['Authorization'] = 'Bearer ' + token;
              }
              return next(method, input, options);
            },
          },
        ],
      }),
    );

    registerRootStore(this);

    this.user = new User({ username: '', token: '' });
  }

  async runTwirpRequest<I extends object, O extends object>(
    handler: TwirpHandler<I, O>,
    input: I,
    options?: RpcOptions,
    throwRpcErrors?: boolean,
  ): Promise<O | undefined> {
    try {
      return (await handler.bind(this.client)(input, options)).response;
    } catch (e) {
      if (e instanceof RpcError && !throwRpcErrors) {
        presentTwirpError(e.code);
      } else {
        throw e;
      }
    }
  }
}

const globalStateCtx = createContext<GlobalState | null>(null);
globalStateCtx.displayName = 'StateContext';

export const StateProvider = globalStateCtx.Provider;
export function useGlobalState(): GlobalState {
  const ctx = useContext(globalStateCtx);
  if (ctx === null) {
    throw new Error('StateContext is missing!');
  }

  return ctx;
}
