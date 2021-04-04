import { useState } from 'react';
import { Button, NonIdealState, Spinner } from '@blueprintjs/core';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import { History } from 'history';
import { Release } from '@api/mod';
import { GlobalState, useGlobalState } from '../lib/state';
import {launchMod} from '../dialogs/launch-mod';

async function fetchMods(gs: GlobalState): Promise<Release[]> {
  const result = await gs.client.getLocalMods({});
  console.log(result.response.mods);
  return result.response.mods;
}

export interface LocalModListProps {
  history: History;
}
export default observer(function LocalModList(props: LocalModListProps): React.ReactElement {
  const gs = useGlobalState();
  const [modList] = useState(() => fromPromise(fetchMods(gs)));

  return (
    <div className="text-white">
      {modList.case({
        pending: () => <NonIdealState icon={<Spinner />} title="Loading mods..." />,
        rejected: (e) => <NonIdealState icon="error" title="Failed to load mods" description={e?.toString ? e.toString() : e} />,
        fulfilled: (mods) => (
          <div className="flex flex-row flex-wrap justify-between gap-4">
            {mods.map((mod) => (
              <div key={mod.modid} className="mod-tile bg-important flex flex-col overflow-hidden">
                {mod.teaser?.fileid ? 
                  <img src={"https://api.client.fsnebula.org/ref/" + mod.teaser?.fileid} />
                :
                  <img src={require('../resources/modstock.jpg').default} />
                }
                <div className="flex-1 flex flex-col justify-center text-white">
                  <div className="flex-initial text-center overflow-ellipsis overflow-hidden">{mod.title}</div>
                </div>

                <div className="cover flex flex-col justify-center gap-2">
                  <Button onClick={() => launchMod(gs, mod.modid, mod.version)}>Play</Button>
                  <Button onClick={() => props.history.push('/mod/' + mod.modid + '/' + mod.version)}>Details</Button>
                  <Button>Uninstall</Button>
                </div>
              </div>
            ))}{' '}
          </div>
        ),
      })}
    </div>
  );
});
