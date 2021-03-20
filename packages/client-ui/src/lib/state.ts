import { createContext, useContext } from 'react';
import {makeAutoObservable} from 'mobx';
import { RpcError, RpcOptions, UnaryCall } from '@protobuf-ts/runtime-rpc';
import { TwirpFetchTransport } from '@protobuf-ts/twirp-transport';
import { Toaster, IToaster } from '@blueprintjs/core';
import { KnossosClient } from '@api/client.client';
import { TaskTracker } from './task-tracker';

type TwirpHandler<I extends object, O extends object> = (
  input: I,
  options?: RpcOptions,
) => UnaryCall<I, O>;

export class GlobalState {
  toaster: IToaster;
  client: KnossosClient;
  tasks: TaskTracker;

  constructor() {
    this.toaster = Toaster.create({});
    this.client = new KnossosClient(
      new TwirpFetchTransport({
        baseUrl: 'https://api.client.fsnebula.org/twirp',
        deadline: process.env.NODE_ENV === 'production' ? 10000 : 1000,
      }),
    );
    this.tasks = new TaskTracker();
    this.tasks.listen();

    makeAutoObservable(this);
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
