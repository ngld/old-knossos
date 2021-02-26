import {useState, useEffect} from 'react';
import {makeAutoObservable} from 'mobx';
import {LogMessage, ClientSentEvent} from '@api/client';

interface TaskState {
  label: string;
  progress: number;
  status: string;
  error: boolean;
  indeterminate: boolean;
  logMessages: LogMessage[];
}

export class TaskTracker {
  _idCounter: number;
  tasks: TaskState[];
  taskMap: Record<string, TaskState>;

  constructor() {
    this._idCounter = 0;
    this.tasks = [];
    this.taskMap = {};

    makeAutoObservable(this);
  }

  startTask(label: string): number {
    const id = this._idCounter++;
    const task = {
      label,
      progress: 0,
      status: 'Initialising',
      error: false,
      indeterminate: false,
      logMessages: [],
    } as TaskState;

    this.taskMap[id] = task;
    this.tasks.unshift(this.taskMap[id]);

    return id;
  }

  updateTask(ev: ClientSentEvent): void {
    const task = this.taskMap[ev.ref];
    if (!task) {
      console.error(`Got update for missing task ${ev.ref}`);
      return;
    }

    switch(ev.payload.oneofKind) {
      case 'message':
        task.logMessages.push(ev.payload.message);
        break;
      case 'progress':
        const info = ev.payload.progress;
        task.progress = info.progress;
        task.status = info.description;
        task.error = info.error;
        task.indeterminate = info.indeterminate;
        break;
    }

    this.taskMap[ev.ref] = task;
  }
}

export function useTaskTracker(): TaskTracker {
  const [tracker] = useState(() => new TaskTracker());

  useEffect(() => {
    function listener(msg: ArrayBuffer) {
      try {
        const ev = ClientSentEvent.fromBinary(new Uint8Array(msg));
        tracker.updateTask(ev);
      } catch(e) {
        console.error(e);
      }
    }

    // @ts-expect-error TS doesn't know about Knossos' API
    knAddMessageListener(listener);
    // @ts-expect-error TS doesn't know about Knossos' API
    return () => knRemoveMessageListener(listener);
  }, []);

  return tracker;
}
