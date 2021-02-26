import { useState, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import { WakeupResponse, ClientSentEvent } from '@api/client';
import { Button, ProgressBar } from '@blueprintjs/core';

import { GlobalState, useGlobalState } from '../lib/state';
import { useTaskTracker, TaskTracker } from '../lib/task-tracker';

async function fetchInfo(gs: GlobalState): Promise<WakeupResponse | undefined> {
  const response = await gs.runTwirpRequest(gs.client.wakeup, {});
  console.log(response);
  return response;
}

async function runTest(gs: GlobalState): Promise<void> {
  const response = await gs.client.dispatchTest({});
  alert('Done!');
}

async function runSpeedTest(gs: GlobalState, tracker: TaskTracker): Promise<void> {
  const ref = tracker.startTask('Speedtest');
  const response = await gs.client.speedTest({ ref });
  console.log(response);
}

async function runArchiveTest(gs: GlobalState, tracker: TaskTracker): Promise<void> {
  const ref = tracker.startTask('Archive test');
  const response = await gs.client.archiveTest({ ref });
  console.log(response);
}

export default observer(function StartPage(): React.ReactElement {
  const gs = useGlobalState();
  const [state] = useState(() => fromPromise(fetchInfo(gs)));
  const tracker = useTaskTracker();

  return (
    <span>
      {state.case({
        pending: () => <span>Loading...</span>,
        rejected: (e) => <pre>{e.toString()}</pre>,
        fulfilled: (data) => (
          <div>
            {data ? <pre>{JSON.stringify(data, null, 2)}</pre> : <span>No idea</span>}
            <Button onClick={() => runTest(gs)}>Test</Button>
            <Button onClick={() => runSpeedTest(gs, tracker)}>Speedtest</Button>
            <Button onClick={() => runArchiveTest(gs, tracker)}>Archive test</Button>
            <ul>
              {tracker.tasks.map((m, i) => (
                <li key={i}>
                  <strong>{m.label}</strong>
                  <br />
                  {m.status}
                  <br/>
                  <ProgressBar animate={false} value={m.progress} />
                  <div>
                    {m.logMessages.map((line, i) => (
                      <div key={i}>
                        {line.level}: {line.message}
                        <div className="float-right">{line.sender}</div>
                      </div>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ),
      })}
    </span>
  );
});
