import React from 'react';
import { Callout, Divider, Button, Toast } from '@blueprintjs/core';
import type { RouteComponentProps } from 'react-router-dom';
import type { History } from 'history';
import { action } from 'mobx';
import { RpcError } from '@protobuf-ts/runtime-rpc';

import type { BoolResponse } from '@api/service';
import { useGlobalState, GlobalState } from '../lib/state';
import { alert } from '../lib/alert';
import { presentTwirpError } from '../lib/twirp-helpers';

interface VerifyMailParams {
  token: string;
}

async function sendValidation(gs: GlobalState, history: History, token: string): Promise<void> {
  const response = await gs.runTwirpRequest(gs.client.verifyAccount, {
    token,
  });

  if (response?.success) {
    
  }
}

export default function RegisterPage(props: RouteComponentProps): React.ReactElement {
  const gs = useGlobalState();

  return (
    <div className="flex container gap-4">
      <div className="flex-1">
        <Form
          initialState={
            {
              user: '',
              email: '',
              password: '',
              passwordRepeat: '',
            } as FormState
          }
          onValidate={validate}
          onSubmit={(s, d) => submitForm(s, d, props.history, gs)}
        >
          <Field name="user" label="Username" required />
          <Field name="email" label="E-Mail" type="email" required />
          <Field name="password" label="Password" type="password" required />
          <Field
            name="passwordRepeat"
            label="Password repeat"
            type="password"
            helperText="Just repeat the previous password to make sure that you entered it correctly."
            required
          />

          <FormButton type="submit" intent="primary">
            Register
          </FormButton>
        </Form>
      </div>
      <Divider className="flex-initial" />
      <div className="flex-1">
        <Callout title="Important note regarding the E-Mail field">
          You have to specify a valid email address since we'll mail you a validation link to check
          that this address actually belongs to you.
        </Callout>
      </div>
    </div>
  );
}
