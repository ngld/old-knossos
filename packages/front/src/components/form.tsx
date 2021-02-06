import React from 'react';
import { runInAction, action } from 'mobx';
import { useLocalObservable, Observer } from 'mobx-react-lite';
import { nanoid } from 'nanoid/non-secure';
import { IButtonProps, Button, Spinner } from '@blueprintjs/core';
import type { SetOptional } from 'type-fest';
import { RpcOptions, UnaryCall, RpcError } from '@protobuf-ts/runtime-rpc';
import { FormContext, DefaultOptions, FormContextType } from './form-ctx';
import { presentTwirpError } from '../lib/twirp-helpers';

export type Errors<T> = SetOptional<Record<keyof T, string>>;

interface Props<T> {
  className?: string;
  initialState: T;
  defaults?: DefaultOptions;
  onValidate?: (state: T) => Record<string, string | undefined>;
  onSubmit?: (state: T, defaults: DefaultOptions) => void;
  children: React.ReactNode | React.ReactNode[];
}

export function Form<T>(props: Props<T>) {
  const state = useLocalObservable(() => ({
    state: Object.assign({}, props.initialState),
    uid: nanoid(),
    defaults: props.defaults ?? {},
    errors: {},
  })) as FormContextType;

  return (
    <FormContext.Provider value={state}>
      <form
        action="#"
        className={props.className}
        onSubmit={action((ev) => {
          ev.preventDefault();
          const p = props as Props<Record<string, any>>;
          submitHelper(state, p.onValidate, p.onSubmit);
        })}
      >
        {props.children}
        <Observer>{() => (state.defaults.spinning ? <Spinner /> : null)}</Observer>
      </form>
    </FormContext.Provider>
  );
}

function submitHelper(
  ctx: FormContextType,
  validate?: (state: Record<string, any>) => Record<string, string | undefined>,
  submit?: (state: Record<string, any>, defaults: DefaultOptions) => void,
) {
  if (validate) {
    ctx.errors = validate(ctx.state);

    if (Object.keys(ctx.errors).length > 0) {
      return;
    }
  }

  if (submit) {
    submit(ctx.state, ctx.defaults);
  }
}

export function SubmitButton(props: IButtonProps<HTMLButtonElement>): React.ReactElement {
  return <Button type="submit" {...props} />;
}

type TwirpHandler<I extends object, O extends object> = (
  input: I,
  options?: RpcOptions,
) => UnaryCall<I, O>;
export async function twirpRequest<I extends object, O extends object>(
  handler: TwirpHandler<I, O>,
  defaults: DefaultOptions,
  input: I,
  options?: RpcOptions,
): Promise<O | null> {
  runInAction(() => {
    defaults.spinning = true;
    defaults.disabled = true;
  });

  let response: O | null = null;
  try {
    response = (await handler(input, options)).response;
  } catch (e) {
    if (e instanceof RpcError) {
      presentTwirpError(e.code);

      runInAction(() => {
        defaults.spinning = false;
        defaults.disabled = false;
      });
      return null;
    } else {
      throw e;
    }
  }

  runInAction(() => {
    defaults.spinning = false;
  });
  return response;
}

export { default as Field } from './field';
export { default as FormButton } from './form-button';
export type { DefaultOptions };
