import React from 'react';
import { runInAction } from 'mobx';
import type { RouteComponentProps } from 'react-router-dom';
import type { History } from 'history';

import { useGlobalState, GlobalState } from '../lib/state';
import { Form, Field, FormButton, Errors, DefaultOptions, twirpRequest } from '../components/form';

interface FormState {
  user: string;
  password: string;
}

function validate(state: FormState): Errors<FormState> {
  const errors: Errors<FormState> = {};
  for (const [key, value] of Object.entries(state)) {
    if (value === '') {
      errors[key as keyof FormState] = 'This field is required.';
    }
  }

  return errors;
}

async function submitForm(
  state: FormState,
  defaults: DefaultOptions,
  history: History,
  gs: GlobalState,
) {
  const response = await twirpRequest(gs.client.login.bind(gs.client), defaults, {
    username: state.user,
    password: state.password,
  });
  console.log(response);

  if (response === null) {
    return;
  } else if (!response.success) {
    gs.toaster?.show(
      {
        message:
          'The entered username or password are incorrect. Please check your input and try again.',
        intent: 'danger',
      },
      'login-failed',
    );

    runInAction(() => {
      state.password = '';
      defaults.disabled = false;
    });
  } else {
    gs.toaster?.show(
      {
        message: 'Login successful.',
        intent: 'success',
      },
      'login-success',
    );

    void gs.user?.login(response.token);
    history.push('/');
  }
}

export default function LoginPage(props: RouteComponentProps): React.ReactElement {
  const gs = useGlobalState();

  return (
    <div className="max-w-md">
      <Form
        initialState={
          {
            user: '',
            password: '',
          } as FormState
        }
        onValidate={validate}
        onSubmit={(s, d) => submitForm(s, d, props.history, gs)}
      >
        <Field name="user" label="Username" />
        <Field name="password" label="Password" type="password" />
        <FormButton type="submit" intent="primary">
          Login
        </FormButton>{' '}
        <FormButton onClick={() => props.history.push('/login/reset-password')}>
          Reset Password
        </FormButton>
      </Form>
    </div>
  );
}
