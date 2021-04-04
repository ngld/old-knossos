import React, { useState, useMemo } from 'react';
import { observer } from 'mobx-react-lite';
import { fromPromise } from 'mobx-utils';
import type { RouteComponentProps } from 'react-router-dom';
import {
  Spinner,
  Callout,
  Checkbox,
  NonIdealState,
  HTMLSelect,
  HTMLTable,
  Tab,
  Tabs,
} from '@blueprintjs/core';

import { ModInfoResponse, ModDependencySnapshot, FlagInfo, FlagInfo_Flag } from '@api/client';
import { Release } from '@api/mod';

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

async function getModDependencies(
  gs: GlobalState,
  params: ModDetailsParams,
): Promise<ModDependencySnapshot> {
  const response = await gs.client.getModDependencies({
    id: params.modid,
    version: params.version ?? '',
  });
  return response.response;
}

async function getFlagInfos(
  gs: GlobalState,
  params: ModDetailsParams,
): Promise<Record<string, FlagInfo_Flag[]>> {
  const response = await gs.client.getModFlags({ id: params.modid, version: params.version ?? '' });

  const mappedFlags = {} as Record<string, FlagInfo_Flag[]>;
  for (const info of Object.values(response.response.flags)) {
    if (!mappedFlags[info.category]) {
      mappedFlags[info.category] = [];
    }

    mappedFlags[info.category].push(info);
  }
  return mappedFlags;
}

interface DepInfoProps extends ModDetailsParams {
  release?: Release;
}

const DepInfo = observer(function DepInfo(props: DepInfoProps): React.ReactElement {
  const gs = useGlobalState();
  const deps = useMemo(() => fromPromise(getModDependencies(gs, props)), [
    props.modid,
    props.version,
  ]);

  return deps.case({
    pending: () => <span>Loading...</span>,
    rejected: (e) => (
      <Callout intent="danger" title="Error">
        Could not resolve dependencies:
        <br />
        <pre>{e.toString()}</pre>
      </Callout>
    ),
    fulfilled: (response) => (
      <HTMLTable>
        <thead>
          <tr>
            <th>Mod</th>
            <th>Latest Local Version</th>
            <th>Latest Available Version</th>
            <th>Saved Version</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(response.dependencies).map(([modid, version]) => {
            const current = props.release?.dependencySnapshot[modid] ?? '???';
            return (
              <tr key={modid}>
                <td>{modid}</td>
                <td>{version}</td>
                <td>TBD</td>
                <td>
                  <HTMLSelect>
                    {response.available[modid].versions.map((version) => (
                      <option key={version} value={version} selected={current === version}>
                        {version}
                      </option>
                    ))}
                  </HTMLSelect>
                </td>
              </tr>
            );
          })}
        </tbody>
      </HTMLTable>
    ),
  });
});

function renderFlags(flags: FlagInfo_Flag[]): (React.ReactElement | null)[] {
  return flags.map((flag) => (
    <div key={flag.flag}>
      <Checkbox checked={flag.enabled}>
        {flag.label === '' ? flag.flag : flag.label}
        {flag.help && (
          <span className="float-right">
            <a href={flag.help}>?</a>
          </span>
        )}
      </Checkbox>
    </div>
  ));
}

const FlagsInfo = observer(function FlagsInfo(props: DepInfoProps): React.ReactElement {
  const gs = useGlobalState();
  const flags = useMemo(() => fromPromise(getFlagInfos(gs, props)), [props.modid, props.version]);
  const [currentCat, setCurrentCat] = useState<string>('combined');

  return flags.case({
    pending: () => <span>Loading...</span>,
    rejected: (e) => (
      <Callout intent="danger" title="Error">
        Could not fetch flags:
        <br />
        <pre>{e.toString()}</pre>
      </Callout>
    ),
    fulfilled: (mappedFlags) => {
      return (
        <div>
          <div className="pb-2">
            <label className="text-sm pr-4">Category</label>
            <HTMLSelect onChange={(e) => setCurrentCat(e.target.value)}>
              <option key="combined" value="combined">
                All
              </option>
              {Object.keys(mappedFlags).map((cat) => (
                <option key={cat} value={cat} selected={cat === currentCat}>
                  {cat}
                </option>
              ))}
            </HTMLSelect>
          </div>
          <div className="p-4 border-black border">
            {currentCat === 'combined'
              ? Object.entries(mappedFlags).map(([cat, flags]) => (
                  <div key={cat}>
                    <div className="font-bold p-2">{cat}</div>
                    {renderFlags(flags)}
                  </div>
                ))
              : renderFlags(mappedFlags[currentCat] ?? [])}
          </div>
        </div>
      );
    },
  });
});

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

  const rawDesc = (modDetails.value as ModInfoResponse)?.mod?.description;
  const description = useMemo(() => {
    let desc = rawDesc ?? '';
    return { __html: bbparser(desc === '' ? 'No description provided' : desc) };
  }, [rawDesc]);

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
                <div>
                  <h1 className="mb-2 text-white mod-title">
                    <span className="text-3xl">{mod.mod?.title}</span>
                    <HTMLSelect
                      className="ml-2 -mt-2"
                      value={props.match.params.version ?? mod.versions[0]}
                      onChange={(e) => {
                        props.history.push(`/mod/${props.match.params.modid}/${e.target.value}`);
                      }}
                    >
                      {mod.versions.map((version) => (
                        <option
                          key={version}
                          value={version}
                          selected={version === props.match.params.version}
                        >
                          {version}
                        </option>
                      ))}
                    </HTMLSelect>
                  </h1>
                </div>
                <RefImage className="object-contain w-full max-h-300px" src={mod.mod?.banner} />
              </div>
              <Tabs renderActiveTabPanelOnly={true}>
                <Tab
                  id="desc"
                  title="Description"
                  panel={
                    <div className="bg-base p-2 rounded text-white">
                      <p dangerouslySetInnerHTML={description} />
                    </div>
                  }
                />
                <Tab
                  id="deps"
                  title="Dependencies"
                  panel={
                    <div className="bg-base p-2 rounded text-white">
                      <DepInfo
                        release={mod.mod}
                        modid={props.match.params.modid}
                        version={props.match.params.version}
                      />
                    </div>
                  }
                />
                <Tab
                  id="flags"
                  title="Flags"
                  panel={
                    <div className="bg-base p-2 rounded text-white">
                      <FlagsInfo
                        release={mod.mod}
                        modid={props.match.params.modid}
                        version={props.match.params.version}
                      />
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
