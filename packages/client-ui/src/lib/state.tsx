import { createElement, createContext, useContext } from 'react';
import {makeAutoObservable} from 'mobx';
import { RpcError, RpcOptions, UnaryCall } from '@protobuf-ts/runtime-rpc';
import { TwirpFetchTransport } from '@protobuf-ts/twirp-transport';
import { Toaster, IToaster } from '@blueprintjs/core';
import { KnossosClient } from '@api/client.client';
import { TaskTracker } from './task-tracker';

interface OverlayProps {
  onFinished: () => void;
}

export class GlobalState {
  toaster: IToaster;
  client: KnossosClient;
  tasks: TaskTracker;
  overlays: [React.FunctionComponent<OverlayProps> | React.ComponentClass<OverlayProps>, Record<string, unknown>][];

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
    this.overlays = [];

    makeAutoObservable(this);
  }

  launchOverlay(component: React.FunctionComponent<OverlayProps> | React.ComponentClass<OverlayProps>, props: Record<string, unknown>) {
    this.overlays.push([component, props]);
  }

  removeOverlay(index: number) {
    this.overlays.splice(index, 1);
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
