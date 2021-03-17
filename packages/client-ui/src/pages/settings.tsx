import { useState, useEffect } from 'react';
import { Button, Card, ControlGroup, FormGroup } from '@blueprintjs/core';
import { makeAutoObservable, autorun, runInAction } from 'mobx';
import { Settings, TaskRequest } from '@api/client';
import { GlobalState, useGlobalState } from '../lib/state';
import FormContext from '../elements/form-context';
import { FormCheckbox, FormInputGroup } from '../elements/form-elements';

async function loadSettings(gs: GlobalState, formState: Settings): Promise<void> {
  try {
    const result = await gs.client.getSettings({});
    runInAction(() => {
      Object.assign(formState, result.response);
    });
  } catch (e) {
    console.error(e);
  }
}

async function saveSettings(gs: GlobalState, formState: Settings): Promise<void> {
  try {
    await gs.client.saveSettings(formState);
  } catch (e) {
    console.error(e);
  }
}

async function selectLibraryFolder(gs: GlobalState, formState: Settings): Promise<void> {
  try {
    const result = await knOpenFolder('Please select your library folder', formState.libraryPath);
    if (result !== '' && result !== formState.libraryPath) {
      runInAction(() => {
        formState.libraryPath = result;
      });

      rescanLocalMods(gs);
    }
  } catch (e) {
    console.error(e);
  }
}

async function rescanLocalMods(gs: GlobalState): Promise<void> {
  try {
    const task = gs.tasks.startTask('Scan new library folder...');
    await gs.client.scanLocalMods(TaskRequest.create({ ref: task }));
  } catch (e) {
    console.error(e);
  }
}

export default function SettingsPage(): React.ReactElement {
  const gs = useGlobalState();
  const [formState] = useState<Settings>(() => {
    const defaults = Settings.create();
    makeAutoObservable(defaults);
    return defaults;
  });

  useEffect(() => {
    void loadSettings(gs, formState);

    return autorun(() => {
      console.log('Settings changed...');
      void saveSettings(gs, formState);
    });
  }, []);

  return (
    <div className="text-white text-sm">
      <FormContext value={(formState as unknown) as Record<string, unknown>}>
        <div className="flex flex-row gap-4">
          <Card className="flex-1">
            <h5 className="text-xl mb-5">General Knossos Settings</h5>
            <FormGroup label="Library Path">
              <ControlGroup fill={true}>
                <FormInputGroup name="libraryPath" readOnly={true} />
                <Button
                  onClick={() => {
                    selectLibraryFolder(gs, formState);
                  }}
                >
                  Browse...
                </Button>
              </ControlGroup>
              <Button
                onClick={() => {
                  rescanLocalMods(gs);
                }}
              >
                Rescan local mods
              </Button>
            </FormGroup>
            <FormCheckbox name="updateCheck" label="Update Notifications" />
            <FormCheckbox name="errorReports" label="Send Error Reports" />
          </Card>
          <div className="flex-1">TODO</div>
        </div>
      </FormContext>
    </div>
  );
}
