import { useState, useEffect, useLayoutEffect, useRef } from 'react';
import { Classes, Button, Dialog, ProgressBar, Text } from '@blueprintjs/core';
import { CiTimesLine } from '@meronex/icons/ci';
import { Tooltip2 } from '@blueprintjs/popover2';
import { observer } from 'mobx-react-lite';
import { LogMessage } from '@api/client';
import { useGlobalState } from '../lib/state';
import { TaskState, logLevelMap } from '../lib/task-tracker';

function getLogTime(task: TaskState, line: LogMessage): string {
  const time = line.time;
  if (!time) {
    return '00:00';
  }

  const duration = time.seconds - task.started;
  const minutes = Math.floor(duration / 60);
  const seconds = duration % 60;

  let result = (minutes < 10 ? '0' : '') + minutes + ':';
  result += (seconds < 10 ? '0' : '') + seconds;
  return result;
}

interface LogBoxProps {
  task: TaskState;
}
function LogBox({ task }: LogBoxProps): React.ReactElement {
  const boxRef = useRef<HTMLDivElement>(null);
  const isBottom = useRef<boolean>(true);

  useLayoutEffect(() => {
    const box = boxRef.current;
    if (box && isBottom.current) {
      box.scrollTop = box.scrollHeight;
    }
  });

  const scrollHandler = () => {
    const box = boxRef.current;
    if (box) {
      // 10 pixel tolerance
      isBottom.current = box.scrollTop + box.clientHeight + 10 >= box.scrollHeight;
    }
  };

  return (
    <div ref={boxRef} className="overflow-y-auto max-h-56 bg-base text-xs" onScroll={scrollHandler}>
      {task.logMessages.map((item, idx) => (
        <div key={idx} title={item.sender} className={'log-' + (logLevelMap[item.level].toLowerCase() ?? 'info')}>
          <span className="font-mono">[{getLogTime(task, item)}]:</span> {item.message}
        </div>
      ))}
    </div>
  );
}

export default observer(function TaskDisplay(): React.ReactElement {
  const gs = useGlobalState();
  const [open, setOpen] = useState<boolean>(false);
  useEffect(() => {
    const listener = () => setOpen(true);
    gs.tasks.on('new', listener);

    return () => void gs.tasks.off('new', listener);
  }, []);

  return (
    <div className="absolute bottom-0 right-40">
      <Tooltip2 content="Show active tasks">
        <div
          className={'cursor-pointer ' + (gs.tasks.active > 0 ? 'text-white' : 'text-dim')}
          onClick={() => setOpen(!open)}
        >
          {gs.tasks.active === 0
            ? 'No active tasks'
            : gs.tasks.active > 1
            ? `${gs.tasks.active} background tasks`
            : gs.tasks.tasks[0].label}
        </div>
      </Tooltip2>
      <Dialog isOpen={open} onClose={() => setOpen(false)} title="Tasks" className="large-dialog">
        <div className={Classes.DIALOG_BODY}>
          {gs.tasks.tasks.map((task) => (
            <div key={task.id}>
              <div className="relative">
                <Text className="mb-1" ellipsize={true}>
                  {task.label}
                </Text>
                {(task.progress === 1 || task.error) && (
                  <div className="absolute right-0 top-0">
                    <Button
                      minimal={true}
                      small={true}
                      onClick={() => gs.tasks.removeTask(task.id)}
                    >
                      <CiTimesLine />
                    </Button>
                  </div>
                )}
              </div>
              <ProgressBar
                stripes={task.indeterminate}
                value={task.indeterminate ? 1 : task.progress}
                intent={task.error ? 'danger' : task.progress === 1 ? 'success' : 'primary'}
              />
              <LogBox task={task} />
            </div>
          ))}
        </div>
      </Dialog>
    </div>
  );
});
