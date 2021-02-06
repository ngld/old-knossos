import React, {useEffect} from 'react';
import type { RouteComponentProps } from 'react-router-dom';
import {H1, Spinner} from '@blueprintjs/core';

import { useGlobalState } from '../lib/state';

export default function LoginPage(props: RouteComponentProps): React.ReactElement {
  const gs = useGlobalState();

  useEffect(() => {
    gs.user?.logout();
    props.history.push('/');

    gs.toaster.show({
      message: `You're now logged out.`,
      intent: 'success',
    });
  }, []);

  return (
    <div className="max-w-md">
      <H1>We're logging you out...</H1>
	  <Spinner intent="primary" />
    </div>
  );
}
