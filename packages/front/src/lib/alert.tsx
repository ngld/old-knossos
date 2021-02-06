import React from 'react';
import { observable, action } from 'mobx';
import { observer } from 'mobx-react-lite';
import { Alert, IAlertProps } from '@blueprintjs/core';
import { nanoid } from 'nanoid';

interface AlertProps extends IAlertProps {
  key: string;
  children: React.ReactNode | React.ReactNode[];
}

const alerts = observable([] as AlertProps[]);

function AlertContainer_(): React.ReactElement {
  return (
    <>
      {alerts.map((data, i) => (
        <Alert
          {...data}
          onClose={action((c, e) => {
            data.isOpen = false;
            if (data.onClose) {
              data.onClose(c, e);
            }
          })}
          onClosed={action((node) => {
            alerts.remove(data);
            if (data.onClosed) {
              data.onClosed(node);
            }
          })}
        />
      ))}
    </>
  );
}

function alert_(data: Omit<AlertProps, 'isOpen' | 'key'>): void {
  const props = data as AlertProps;
  props.isOpen = true;
  props.key = nanoid();
  alerts.push(props);
}

export const AlertContainer = observer(AlertContainer_);
export const alert = action(alert_);
