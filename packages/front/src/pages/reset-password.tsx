import React from 'react';
import { runInAction } from 'mobx';
import type { RouteComponentProps } from 'react-router-dom';
import type { History } from 'history';

import { useGlobalState, GlobalState } from '../lib/state';
import { Form, Field, FormButton, Errors, DefaultOptions, twirpRequest } from '../components/form';

interface FormState {
  email: string;
}

function validate(state: FormState): Errors<FormState> {
  if (state.email === '') {
    return { email: 'This field is required.' };
  } else {
    return {};
  }
}

async function submitForm(
  state: FormState,
  defaults: DefaultOptions,
  history: History,
  gs: GlobalState,
) {
  const response = await twirpRequest(gs.client.startPasswordReset.bind(gs.client), defaults, {
    email: state.email,
  });

  if (!response?.success) {
    gs.toaster.show(
      {
        message: 'Something went wrong. Please contact an admin.',
        intent: 'danger',
      },
      'reset-password-failed',
    );

    runInAction(() => {
      defaults.disabled = false;
    });
  } else {
    gs.toaster.show(
      {
        message:
          'The password reset was successful. Please check your email inbox to get the reset link.',
        intent: 'success',
      },
      'reset-password-success',
    );
  }
}

export default function ResetPasswordPage(props: RouteComponentProps): React.ReactElement {
  const gs = useGlobalState();

  return (
    <div className="max-w-md">
      <Form
        initialState={
          {
            email: '',
          } as FormState
        }
        onValidate={validate}
        onSubmit={(s, d) => submitForm(s, d, props.history, gs)}
      >
        <Field name="email" label="E-Mail" />
        <FormButton type="submit" intent="primary">
          Reset Password
        </FormButton>
      </Form>
    </div>
  );
}
