import { useState } from 'react';
import { NonIdealState, Spinner } from '@blueprintjs/core';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import { SimpleModList_Item } from '@api/client';
import { GlobalState, useGlobalState } from '../lib/state';

async function fetchMods(gs: GlobalState): Promise<SimpleModList_Item[]> {
  const result = await gs.client.getLocalMods({});
  console.log(result.response.mods);
  return result.response.mods;
}

export default observer(function LocalModList(): React.ReactElement {
  const gs = useGlobalState();
  const [modList] = useState(() => fromPromise(fetchMods(gs)));

  return (
    <div className="text-white">
      {modList.case({
        pending: () => <NonIdealState icon={<Spinner />} title="Loading mods..." />,
        rejected: (e) => <NonIdealState icon="error" title="Failed to load mods" description={e?.toString ? e.toString() : e} />,
        fulfilled: (mods) => (
          <div>
            {mods.map((mod) => (
              <div key={mod.id} className="mod-tile bg-important flex flex-col">
                <img src={mod.tile} />
                <div className="flex-1 flex flex-col justify-center text-white">
                  <div className="flex-initial text-center">{mod.title}</div>
                </div>
              </div>
            ))}{' '}
          </div>
        ),
      })}
    </div>
  );
});
