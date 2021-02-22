import { createContext, useContext } from 'react';
import { model, Model, prop, registerRootStore } from 'mobx-keystone';
import { RpcError, RpcOptions, UnaryCall } from '@protobuf-ts/runtime-rpc';
import { TwirpFetchTransport } from '@protobuf-ts/twirp-transport';
import { Toaster, IToaster } from '@blueprintjs/core';
import { KnossosClient } from '@api/client';

type TwirpHandler<I extends object, O extends object> = (
  input: I,
  options?: RpcOptions,
) => UnaryCall<I, O>;


@model('nebula/GlobalState')
export class GlobalState extends Model({
}) {
  // @ts-expect-error TypeScript can't know that onInit() is called before we can access this
  client: KnossosClient;
  // @ts-expect-error See above
  toaster: IToaster;

  onInit() {
    this.toaster = Toaster.create({});
    this.client = new KnossosClient(
      new TwirpFetchTransport({
        baseUrl: 'https://api.client.fsnebula.org/twirp',
        deadline: process.env.NODE_ENV === 'production' ? 10000 : 1000,
      }),
    );

    registerRootStore(this);
  }

  async runTwirpRequest<I extends object, O extends object>(
    handler: TwirpHandler<I, O>,
    input: I,
    options?: RpcOptions,
    throwRpcErrors?: boolean,
  ): Promise<O | undefined> {
    try {
      return (await handler.call(this.client, input, options)).response;
    } catch (e) {
      if (e instanceof RpcError && !throwRpcErrors) {
        console.log(e);
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
