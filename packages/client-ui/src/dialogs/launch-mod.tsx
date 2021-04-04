import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import { Alert, Callout, ProgressBar } from '@blueprintjs/core';
import { GlobalState, useGlobalState } from '../lib/state';

async function performLaunch(gs: GlobalState, props: LaunchModProps): Promise<void> {
  if (!props.modid) {
    throw new Error('Missing mod ID!');
  }

  if (!props.version) {
    throw new Error('Missing mod version!');
  }

  await gs.client.launchMod({
    modid: props.modid,
    version: props.version,
  });
}

interface LaunchModProps {
  modid?: string;
  version?: string;
  onFinished: () => void;
}

const LaunchMod = observer(function LaunchMod(props: LaunchModProps): React.ReactElement {
  const gs = useGlobalState();
  const [isOpen, setOpen] = useState(true);
  const [state] = useState(() => fromPromise(performLaunch(gs, props)));

  return (
    <Alert
      className="large-dialog"
      isOpen={isOpen}
      onClose={() => setOpen(false)}
      onClosed={() => {
        if (props.onFinished) {
          props.onFinished();
        }
      }}
    >
      {state.case({
        pending: () => (
          <>
            <div className="text-lg text-white">Launching FSO...</div>
            <ProgressBar intent="primary" stripes={true} animate={true} value={1} />
          </>
        ),
        fulfilled: () => <span>Done</span>,
        rejected: (e) => (
          <Callout intent="danger" title="Failed to launch FSO">
            <pre>{e.toString()}</pre>
          </Callout>
        ),
      })}
    </Alert>
  );
});

export function launchMod(gs: GlobalState, modid: string, version: string): void {
  gs.launchOverlay(LaunchMod, { modid, version });
}
