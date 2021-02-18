import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import { WakeupResponse } from '@api/client';

import { GlobalState, useGlobalState } from '../lib/state';

async function fetchInfo(gs: GlobalState): Promise<WakeupResponse | undefined> {
  const response = await gs.runTwirpRequest(gs.client.wakeup, {});
  return response;
}

export default observer(function StartPage(): React.ReactElement {
  const gs = useGlobalState();
  const [state] = useState(() => fromPromise(fetchInfo(gs)));

  return (
    <span>
      {state.case({
        pending: () => <span>Loading...</span>,
        rejected: (e) => <pre>{e.toString()}</pre>,
        fulfilled: (data) =>
          data ? <pre>{JSON.stringify(data, null, 2)}</pre> : <span>No idea</span>,
      })}
    </span>
  );
});
