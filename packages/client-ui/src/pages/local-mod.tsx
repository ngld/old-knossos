import React, { useState, useMemo } from 'react';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import type { RouteComponentProps } from 'react-router-dom';
import { Spinner, Callout, NonIdealState, HTMLSelect, Tab, Tabs, H3, UL } from '@blueprintjs/core';

import { ModInfoResponse } from '@api/client';
import RefImage from '../elements/ref-image';
import { useGlobalState, GlobalState } from '../lib/state';
import bbparser from '../lib/bbparser';

async function getModDetails(gs: GlobalState, params: ModDetailsParams): Promise<ModInfoResponse> {
  const response = await gs.client.getModInfo({
    id: params.modid,
    version: params.version ?? '',
  });
  return response.response;
}

export interface ModDetailsParams {
  modid: string;
  version?: string;
}

export default observer(function ModDetailsPage(
  props: RouteComponentProps<ModDetailsParams>,
): React.ReactElement {
  const gs = useGlobalState();
  const modDetails = useMemo(() => fromPromise(getModDetails(gs, props.match.params)), [
    props.match.params,
  ]);
  const [selectedVersion, setVersion] = useState('unknown');
  const description = useMemo(
    () => ({ __html: bbparser((modDetails.value as ModInfoResponse)?.mod?.description ?? '') }),
    [modDetails.value?.mod?.description],
  );

  return (
    <div>
      {modDetails.case({
        pending: () => <Spinner />,
        rejected: (e) => (
          <Callout intent="danger" title="Failed to fetch mod info">
            Unfortunately, the mod details request failed. Please try again.
          </Callout>
        ),
        fulfilled: (mod) =>
          !mod ? (
            <NonIdealState
              icon="warning-sign"
              title="Mod not found"
              description="We couldn't find a mod for this URL."
            />
          ) : (
            <>
              <div className="relative">
                <RefImage src={mod.mod?.banner} />
                <div className="absolute top-0 left-0 p-5 text-white">
                  <h1 className="text-3xl mb-4 text-white">{mod.mod?.title}</h1>
                  <div>
                    <span className="pr-4">Version: </span>
                    <HTMLSelect
                      value={selectedVersion}
                      onChange={(e) => {
                        setVersion(e.target.value);
                        props.history.push(`/mod/${props.match.params.modid}/${e.target.value}`);
                      }}
                    >
                      <option>TODO</option>
                    </HTMLSelect>
                  </div>
                  {/*<div>
                    <span className="pr-4">Last update:</span>
                    <span>{mod.updated?.seconds}</span>
                  </div>*/}
                </div>
              </div>
              <Tabs>
                <Tab
                  id="desc"
                  title="Description"
                  panel={
                    <div className="bg-base p-2 rounded text-white">
                      <p dangerouslySetInnerHTML={description} />
                    </div>
                  }
                />
              </Tabs>
            </>
          ),
      })}
    </div>
  );
});
