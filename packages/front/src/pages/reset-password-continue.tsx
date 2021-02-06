import React, { useState } from 'react';
import { runInAction } from 'mobx';
import { fromPromise } from 'mobx-utils';
import { observer } from 'mobx-react-lite';
import type { RouteComponentProps } from 'react-router-dom';
import type { History } from 'history';
import type { TokenResponse } from '@api/service';
import { RpcError } from '@protobuf-ts/runtime-rpc';
import { Spinner, Callout, Button } from '@blueprintjs/core';

import { useGlobalState, GlobalState } from '../lib/state';
import { presentTwirpError } from '../lib/twirp-helpers';
import { Form, Field, FormButton, Errors, DefaultOptions, twirpRequest } from '../components/form';

interface FormState {
  token: string;
  password: string;
  passwordRepeat: string;
}

function validate(state: FormState): Errors<FormState> {
  const errors: Errors<FormState> = {};

  if (state.password === '') {
    errors.password = 'This field is required.';
  }

  if (state.passwordRepeat === '') {
    errors.passwordRepeat = 'This field is required.';
  } else if (state.password !== state.passwordRepeat) {
    errors.passwordRepeat = 'The entered password do not match.';
  }

  return errors;
}

async function submitForm(
  state: FormState,
  defaults: DefaultOptions,
  history: History,
  gs: GlobalState,
) {
  const response = await twirpRequest(gs.client.resetPassword.bind(gs.client), defaults, {
    token: state.token,
    password: state.password,
  });

  if (!response?.success) {
    gs.toaster.show(
      {
        message: 'Something went wrong. Please contact an admin.',
        intent: 'danger',
      },
      'reset-password-continue-failed',
    );

    runInAction(() => {
      defaults.disabled = false;
    });
  } else {
    gs.toaster.show(
      {
        message: 'The password reset was successful. Please login with your new password.',
        intent: 'success',
      },
      'reset-password-continue-success',
    );

    history.push('/login');
  }
}

async function prepare(gs: GlobalState, token: string): Promise<string> {
  let response: TokenResponse | null = null;
  try {
    response = (await gs.client.preparePasswordReset({ token })).response;
  } catch (e) {
    console.log(e);

    if (e instanceof RpcError) {
      presentTwirpError(e.code);
    } else {
      gs.toaster.show({
        message: 'Something went wrong. Please reload the page.',
        intent: 'danger',
      });
      throw e;
    }
  }

  return response?.token ?? '';
}

export interface ResetPasswordParams {
  token: string;
}

export default observer(function ResetPasswordPage(
  props: RouteComponentProps<ResetPasswordParams>,
): React.ReactElement {
  const gs = useGlobalState();
  const [info] = useState(() => fromPromise(prepare(gs, props.match.params.token)));

  return (
    <div className="max-w-md">
      {info.case({
        pending: () => (
          <div>
            Please wait...
            <Spinner />
          </div>
        ),
        rejected: () => (
          <Callout intent="danger" title="Error">
            The request failed.
          </Callout>
        ),
        fulfilled: (token) =>
          token === '' ? (
            <Callout intent="danger" title="Error">
              <p>The link you used is no longer valid. Please request a new password reset.</p>
              <Button
                intent="primary"
                onClick={(e: React.MouseEvent) => {
                  e.preventDefault();
                  props.history.push('/login/password-reset');
                }}
              >
                Reset Password
              </Button>
            </Callout>
          ) : (
            <Form
              initialState={
                {
                  password: '',
                  passwordRepeat: '',
                  token,
                } as FormState
              }
              onValidate={validate}
              onSubmit={(s, d) => submitForm(s, d, props.history, gs)}
            >
              <Field name="password" label="Password" type="password" />
              <Field
                name="passwordRepeat"
                label="Password repeat"
                type="password"
                helperText="Just repeat the previous password to make sure that you entered it correctly."
              />

              <FormButton type="submit" intent="primary">
                Reset Password
              </FormButton>
            </Form>
          ),
      })}
    </div>
  );
});
