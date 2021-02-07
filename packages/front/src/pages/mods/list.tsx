import React, { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import type { RouteComponentProps } from 'react-router-dom';
import { Spinner, Callout, NonIdealState, Card } from '@blueprintjs/core';

import { useGlobalState, GlobalState } from '../../lib/state';

async function listMods(gs: GlobalState) {
  const response = await gs.runTwirpRequest(gs.client.getModList, {
    limit: 100,
    offset: 0,
    query: '',
  });

  return response;
}

export default observer(function ModListPage(props: RouteComponentProps): React.ReactElement {
  const gs = useGlobalState();
  const [modList] = useState(() => fromPromise(listMods(gs)));

  return (
    <div>
      {modList.case({
        pending: () => <Spinner />,
        rejected: (e) => (
          <Callout intent="danger" title="Failed to fetch mods">
            Unfortunately, the mod list request failed. Please try again.
          </Callout>
        ),
        fulfilled: (mods) =>
          !mods ? (
            <NonIdealState
              icon="search"
              title="No mods found"
              description="We couldn't find any mods matching your request."
            />
          ) : (
            <div className="flex flex-wrap">
              {mods.mods.map((mod) => (
                <div key={mod.modid} className="flex-initial bg-bg-tile m-2 mod-tile">
                  <a href="#" className="block text-center no-underline pb-2">
                    <img src={mod.teaser} className="mx-auto mb-2" />
                    {mod.title}
                  </a>
                </div>
              ))}
            </div>
          ),
      })}
    </div>
  );
});
