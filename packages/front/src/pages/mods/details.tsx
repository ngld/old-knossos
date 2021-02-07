import React, { useState, useMemo } from 'react';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import type { RouteComponentProps } from 'react-router-dom';
import { Spinner, Callout, NonIdealState, HTMLSelect, Tab, Tabs, H3, UL } from '@blueprintjs/core';

import { useGlobalState, GlobalState } from '../../lib/state';
import bbparser from '../../lib/bbparser';

async function getModDetails(gs: GlobalState, params: ModDetailsParams) {
  const response = await gs.runTwirpRequest(gs.client.getModDetails, {
    latest: !params.version,
    modid: params.modid,
    version: params.version ?? '',
    requestDownloads: true,
  });

  return response;
}

export interface ModDetailsParams {
  modid: string;
  version?: string;
}

export default observer(function ModDetailsPage(
  props: RouteComponentProps<ModDetailsParams>,
): React.ReactElement {
  const gs = useGlobalState();
  const modDetails = useMemo(() => fromPromise(getModDetails(gs, props.match.params)), [props.match.params]);
  const [selectedVersion, setVersion] = useState('unknown');
  const description = useMemo(() => ({ __html: bbparser(modDetails.value?.description ?? '') }), [
    modDetails.value?.description,
  ]);

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
                <img src={mod.banner} />
                <div className="absolute top-0 left-0 p-5 text-white">
                  <h1 className="text-3xl mb-4 text-white">{mod.title}</h1>
                  <div>
                    <span className="pr-4">Version: </span>
                    <HTMLSelect
                      value={selectedVersion}
                      onChange={(e) => {
                        setVersion(e.target.value);
                        props.history.push(`/mod/${props.match.params.modid}/${e.target.value}`);
                      }}
                    >
                      {mod.versions.map((version) => (
                        <option key={version} value={version}>
                          {version}
                        </option>
                      ))}
                    </HTMLSelect>
                  </div>
                  {/*<div>
                    <span className="pr-4">Last update:</span>
                    <span>{mod.updated?.seconds}</span>
                  </div>*/}
                </div>
              </div>
              <Tabs>
                <Tab id="desc" title="Description" panel={<p dangerouslySetInnerHTML={description} />} />
                <Tab
                  id="dl"
                  title="Downloads"
                  panel={
                    <div>
                      {mod.downloads.map((pkg) => (
                        <div key={pkg.name}>
                          <H3>{pkg.name}</H3>
                          {pkg.notes}
                          <UL className="list-disc">
                            {pkg.archives.map((archive) => (
                              <li key={archive.label}>
                                {archive.label + ': '}
                                {archive.links.map((link, idx) => (
                                  <>
                                    {idx === 0 ? null : ' | '}
                                    <a href={link}>
                                      {(/https?:\/\/([^/]+)/.exec(link) ?? [''])[1]}
                                    </a>
                                  </>
                                ))}
                                <br/>
                                SHA256: {archive.checksum}
                              </li>
                            ))}
                          </UL>
                        </div>
                      ))}
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
