import { useState, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import { WakeupResponse, ClientSentEvent } from '@api/client';
import { Button, ProgressBar } from '@blueprintjs/core';

import { GlobalState, useGlobalState } from '../lib/state';

async function fetchInfo(gs: GlobalState): Promise<WakeupResponse | undefined> {
  const response = await gs.runTwirpRequest(gs.client.wakeup, {});
  console.log(response);
  return response;
}

async function runTest(gs:GlobalState): Promise<void> {
  const response = await gs.client.dispatchTest({});
  alert('Done!');
}

export default observer(function StartPage(): React.ReactElement {
  const gs = useGlobalState();
  const [state] = useState(() => fromPromise(fetchInfo(gs)));
  const [messages, setMessages] = useState([] as ClientSentEvent[]);

  useEffect(() => {
    function listener(msg: ArrayBuffer) {
      const ev = ClientSentEvent.fromBinary(new Uint8Array(msg));
      setMessages((m) => [...m, ev]);
    }

    // @ts-expect-error TS doesn't know about Knossos' API
    knAddMessageListener(listener);
    // @ts-expect-error TS doesn't know about Knossos' API
    return () => knRemoveMessageListener(listener);
  }, []);

  return (
    <span>
      {state.case({
        pending: () => <span>Loading...</span>,
        rejected: (e) => <pre>{e.toString()}</pre>,
        fulfilled: (data) =>
          <div>
            {data ? <pre>{JSON.stringify(data, null, 2)}</pre> : <span>No idea</span>}
            <button onClick={() => runTest(gs)}>Test</button>
            <ul>
              {messages.map((m, i) => <li key={i}>{JSON.stringify(m)}</li>)}
            </ul>
          </div>,
      })}
    </span>
  );
});
